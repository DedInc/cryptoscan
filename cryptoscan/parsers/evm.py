"""
EVM-compatible chain parser (Ethereum, BSC, Polygon, etc.).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from ..config import BLOCKS_PER_TX_MULTIPLIER, MAX_BLOCKS_TO_SCAN
from ..exceptions import BlockFetchError
from ..models import PaymentInfo, PaymentStatus
from ..security import mask_address, mask_transaction_id
from .base import ChainParser

logger = logging.getLogger(__name__)


class EVMParser(ChainParser):
    """Parser for EVM-compatible chains (Ethereum, BSC, Polygon, etc.)."""

    async def get_transactions(
        self, address: str, limit: int, expected_amount: Optional[Decimal] = None
    ) -> List[PaymentInfo]:
        """Get EVM transactions"""
        await self.client.connect()

        latest_block = await self.client.call("eth_blockNumber")
        latest_block_num = int(latest_block, 16)
        logger.info(
            f"Scanning from block #{latest_block_num} for address {mask_address(address)}"
        )

        transactions = []
        # Check recent blocks (MAX_BLOCKS_TO_SCAN blocks = ~20 minutes on ETH)
        blocks_to_check = min(limit * BLOCKS_PER_TX_MULTIPLIER, MAX_BLOCKS_TO_SCAN)
        logger.info(f"Will check {blocks_to_check} blocks...")

        for i in range(blocks_to_check):
            try:
                block = await self.client.call(
                    "eth_getBlockByNumber", [hex(latest_block_num - i), True]
                )
                if not block or not block.get("transactions"):
                    continue

                tx_count = len(block.get("transactions", []))
                if i % 20 == 0:
                    logger.debug(
                        f"Checked block #{latest_block_num - i}, {tx_count} txs, found {len(transactions)} matches so far"
                    )

                for tx in block["transactions"]:
                    to_addr = tx.get("to") or ""
                    if to_addr.lower() == address.lower():
                        payment = self.parse_transaction(
                            tx, block, latest_block_num=latest_block_num
                        )
                        amount = payment.amount
                        logger.info(
                            f"Found TX: {mask_transaction_id(tx['hash'])}, amount: {amount} {self.currency_symbol}, confirmations: {payment.confirmations}"
                        )

                        # If expected_amount provided, return immediately on match
                        if expected_amount is not None:
                            if amount.normalize() == expected_amount.normalize():
                                logger.info(
                                    f"MATCH! Amount {amount} matches expected {expected_amount}"
                                )
                                return [payment]

                        transactions.append(payment)
                        if len(transactions) >= limit:
                            return transactions
            except BlockFetchError:
                raise
            except Exception as e:
                logger.debug(f"Error checking block {latest_block_num - i}: {e}")
                continue

        logger.info(
            f"Scan complete. Found {len(transactions)} transactions to {mask_address(address)}"
        )
        return transactions

    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get single EVM transaction"""
        await self.client.connect()
        try:
            tx = await self.client.call("eth_getTransactionByHash", [tx_id])
            if not tx:
                return None
            receipt = await self.client.call("eth_getTransactionReceipt", [tx_id])
            return self.parse_transaction(tx, receipt=receipt)
        except Exception:
            return None

    def parse_transaction(
        self,
        tx: dict,
        block: dict = None,
        receipt: dict = None,
        latest_block_num: int = None,
    ) -> PaymentInfo:
        """Parse EVM transaction"""
        value_wei = int(tx.get("value", "0x0"), 16)
        amount = Decimal(value_wei) / Decimal(10**self.network_config.decimals)

        block_number = None
        timestamp = datetime.now(timezone.utc)
        if block:
            block_number = int(block.get("number", "0x0"), 16)
            timestamp = datetime.fromtimestamp(int(block.get("timestamp", "0x0"), 16))
        elif tx.get("blockNumber"):
            block_number = int(tx["blockNumber"], 16)

        status = PaymentStatus.CONFIRMED if block_number else PaymentStatus.PENDING
        if receipt and receipt.get("status") == "0x0":
            status = PaymentStatus.FAILED

        # Calculate confirmations
        confirmations = 0
        if block_number and latest_block_num:
            confirmations = latest_block_num - block_number + 1
        elif block_number:
            confirmations = 1  # At least 1 if it's in a block

        return PaymentInfo(
            transaction_id=tx["hash"],
            wallet_address=tx.get("to", ""),
            amount=amount,
            currency=self.currency_symbol,
            status=status,
            timestamp=timestamp,
            block_height=block_number,
            confirmations=confirmations,
            fee=None,
            from_address=tx.get("from", ""),
            to_address=tx.get("to", ""),
            raw_data={"tx": tx, "receipt": receipt, "block": block},
        )
