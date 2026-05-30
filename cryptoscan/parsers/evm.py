"""EVM-compatible chain parser (Ethereum, BSC, Polygon, etc.)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from ..core.exceptions import (
    BlockFetchError,
    CSConnectionError,
    CSTimeoutError,
    RPCError,
)
from ..core.models import (
    MatchMode,
    PaymentInfo,
    PaymentStatus,
    TokenConfig,
    match_amount,
)
from ..security import mask_address, mask_transaction_id
from .base import ChainParser
from .evm_tokens import (
    is_transfer_to_wallet,
    parse_log_amount,
    parse_token_payment_from_log,
    resolve_token_config_for_evm,
)

__all__ = ["EVMParser"]

logger = logging.getLogger(__name__)

_NETWORK_ERRORS = (RPCError, CSConnectionError, CSTimeoutError)
_PARSE_ERRORS = (KeyError, ValueError, TypeError)


def _resolve_token_address(token_contract: str | TokenConfig | None) -> str | None:
    if token_contract is None:
        return None
    if isinstance(token_contract, TokenConfig):
        return token_contract.contract_address
    return token_contract


class EVMParser(ChainParser):
    """Parser for EVM-compatible chains (Ethereum, BSC, Polygon, etc.)."""

    async def get_transactions(
        self,
        address: str,
        limit: int,
        expected_amount: Decimal | None = None,
        match_mode: MatchMode | None = None,
        token_contract: str | TokenConfig | None = None,
    ) -> list[PaymentInfo]:
        await self.client.connect()
        mode = match_mode or MatchMode.EXACT
        latest_block = await self.client.call("eth_blockNumber")
        latest_block_num = int(latest_block, 16)
        token_display = _resolve_token_address(token_contract)
        logger.info(
            "Scanning from block #%s for address %s (mode=%s, token=%s)",
            latest_block_num,
            mask_address(address),
            mode.value,
            mask_address(token_display) if token_display else "native",
        )
        transactions: list[PaymentInfo] = []
        blocks_to_check = min(
            limit * self.client.config.blocks_per_tx_multiplier,
            self.client.config.max_blocks_to_scan,
        )
        for i in range(blocks_to_check):
            result = await self._scan_single_block(
                latest_block_num - i,
                address,
                latest_block_num,
                expected_amount,
                mode,
                token_contract,
                transactions,
                limit,
                i,
            )
            if result is not None:
                return result
        logger.info(
            "Scan complete. Found %s transactions to %s",
            len(transactions),
            mask_address(address),
        )
        return transactions

    async def _scan_single_block(
        self,
        block_num: int,
        address: str,
        latest_block_num: int,
        expected_amount: Decimal | None,
        mode: MatchMode,
        token_contract: str | TokenConfig | None,
        transactions: list[PaymentInfo],
        limit: int,
        idx: int,
    ) -> list[PaymentInfo] | None:
        try:
            block = await self.client.call(
                "eth_getBlockByNumber", [hex(block_num), True]
            )
            if not block or not block.get("transactions"):
                return None
            if idx % 20 == 0:
                logger.debug(
                    "Checked block #%s, %s txs, found %s matches so far",
                    block_num,
                    len(block.get("transactions", [])),
                    len(transactions),
                )
            for tx in block["transactions"]:
                for payment in await self._match_transaction(
                    tx, block, address, latest_block_num, token_contract
                ):
                    logger.info(
                        "Found TX: %s, amount: %s %s, confirmations: %s",
                        mask_transaction_id(payment.transaction_id),
                        payment.amount,
                        payment.currency,
                        payment.confirmations,
                    )
                    if expected_amount is not None and match_amount(
                        payment.amount, expected_amount, mode
                    ):
                        logger.info(
                            "MATCH! Amount %s matches expected %s (mode=%s)",
                            payment.amount,
                            expected_amount,
                            mode.value,
                        )
                        return [payment]
                    transactions.append(payment)
                    if len(transactions) >= limit:
                        return transactions
        except BlockFetchError:
            raise
        except _PARSE_ERRORS as e:
            logger.debug("Error parsing block %s: %s", block_num, e.__class__.__name__)
        except _NETWORK_ERRORS as e:
            logger.debug(
                "Network error checking block %s: %s", block_num, e.__class__.__name__
            )
        return None

    async def _match_transaction(
        self,
        tx: dict,
        block: dict,
        wallet_address: str,
        latest_block_num: int,
        token_contract: str | TokenConfig | None,
    ) -> list[PaymentInfo]:
        to_addr = tx.get("to") or ""
        payments: list[PaymentInfo] = []
        if to_addr.lower() == wallet_address.lower():
            payments.append(
                self.parse_transaction(tx, block, latest_block_num=latest_block_num)
            )
        token_addr = _resolve_token_address(token_contract)
        if token_contract and token_addr and to_addr.lower() == token_addr.lower():
            token_payment = await self._check_token_transfer(
                tx, block, wallet_address, token_contract, latest_block_num
            )
            if token_payment:
                payments.append(token_payment)
        return payments

    async def _check_token_transfer(
        self,
        tx: dict,
        block: dict,
        wallet_address: str,
        token_contract: str | TokenConfig,
        latest_block_num: int,
    ) -> PaymentInfo | None:
        token_address, decimals, symbol = self._resolve_token_config(token_contract)
        try:
            receipt = await self.client.call("eth_getTransactionReceipt", [tx["hash"]])
        except _NETWORK_ERRORS:
            return None
        if not receipt:
            return None
        wallet_padded = "0x" + "0" * 24 + wallet_address.lower()[2:]
        for log in receipt.get("logs", []):
            if not self._is_transfer_to_wallet(log, token_address, wallet_padded):
                continue
            return parse_token_payment_from_log(
                log,
                tx,
                block,
                receipt,
                wallet_address,
                token_address,
                decimals,
                symbol,
                latest_block_num,
            )
        return None

    @staticmethod
    def _is_transfer_to_wallet(
        log: dict, token_contract: str, wallet_padded: str
    ) -> bool:
        return is_transfer_to_wallet(log, token_contract, wallet_padded)

    @staticmethod
    def _parse_log_amount(data: str) -> Decimal:
        return parse_log_amount(data)

    def _resolve_token_config(
        self, token_contract: str | TokenConfig
    ) -> tuple[str, int, str]:
        return resolve_token_config_for_evm(
            token_contract, self.network_config.decimals, self.currency_symbol
        )

    async def get_transaction(self, tx_id: str) -> PaymentInfo | None:
        await self.client.connect()
        try:
            tx = await self.client.call("eth_getTransactionByHash", [tx_id])
            if not tx:
                return None
            receipt = await self.client.call("eth_getTransactionReceipt", [tx_id])
            return self.parse_transaction(tx, receipt=receipt)
        except _NETWORK_ERRORS as e:
            logger.warning(
                "Failed to fetch EVM transaction %s: %s", mask_transaction_id(tx_id), e
            )
            return None
        except _PARSE_ERRORS as e:
            logger.warning(
                "Failed to parse EVM transaction %s: %s", mask_transaction_id(tx_id), e
            )
            return None

    async def get_block_number(self) -> int:
        await self.client.connect()
        return int(await self.client.call("eth_blockNumber", []), 16)

    async def get_block_for_payment(
        self,
        block_identifier: str,
        wallet_address: str,
        expected_amount: Decimal | None,
        latest_block_num: int | None = None,
        match_mode: MatchMode | None = None,
        token_contract: str | TokenConfig | None = None,
    ) -> PaymentInfo | None:
        await self.client.connect()
        mode = match_mode or MatchMode.EXACT
        try:
            block = await self.client.call(
                "eth_getBlockByHash", [block_identifier, True]
            )
            if not block or not block.get("transactions"):
                return None
            if latest_block_num is None:
                latest_block_num = await self.get_block_number()
            for tx in block["transactions"]:
                for payment in await self._match_transaction(
                    tx, block, wallet_address, latest_block_num, token_contract
                ):
                    if match_amount(payment.amount, expected_amount, mode):
                        return payment
        except _NETWORK_ERRORS as e:
            logger.warning(
                "Error fetching block %s: %s",
                block_identifier[:16],
                e.__class__.__name__,
            )
        except _PARSE_ERRORS as e:
            logger.warning(
                "Error parsing block %s: %s",
                block_identifier[:16],
                e.__class__.__name__,
            )
        return None

    def parse_transaction(
        self,
        tx: dict,
        block: dict = None,
        receipt: dict = None,
        latest_block_num: int = None,
    ) -> PaymentInfo:
        value_wei = int(tx.get("value", "0x0"), 16)
        amount = Decimal(value_wei) / Decimal(10**self.network_config.decimals)
        block_number = None
        timestamp = datetime.now(timezone.utc)
        if block:
            block_number = int(block.get("number", "0x0"), 16)
            timestamp = datetime.fromtimestamp(
                int(block.get("timestamp", "0x0"), 16), tz=timezone.utc
            )
        elif tx.get("blockNumber"):
            block_number = int(tx["blockNumber"], 16)
        status = PaymentStatus.CONFIRMED if block_number else PaymentStatus.PENDING
        if receipt and receipt.get("status") == "0x0":
            status = PaymentStatus.FAILED
        confirmations = 0
        if block_number and latest_block_num:
            confirmations = latest_block_num - block_number + 1
        elif block_number:
            confirmations = 1
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
