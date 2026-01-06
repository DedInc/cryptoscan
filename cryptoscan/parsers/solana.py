"""
Solana chain parser.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from ..models import PaymentInfo, PaymentStatus
from .base import ChainParser


class SolanaParser(ChainParser):
    """Parser for Solana transactions."""

    async def get_transactions(
        self, address: str, limit: int, expected_amount: Optional[Decimal] = None
    ) -> List[PaymentInfo]:
        """Get Solana transactions"""
        await self.client.connect()
        signatures = await self.client.call(
            "getSignaturesForAddress", [address, {"limit": limit}]
        )

        transactions = []
        for sig_info in signatures or []:
            tx = await self.get_transaction(sig_info["signature"])
            if tx:
                transactions.append(tx)
        return transactions

    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get Solana transaction"""
        await self.client.connect()
        try:
            result = await self.client.call(
                "getTransaction",
                [tx_id, {"encoding": "json", "maxSupportedTransactionVersion": 0}],
            )
            if not result:
                return None

            return self.parse_transaction(result)
        except Exception:
            return None

    def parse_transaction(self, result: dict) -> Optional[PaymentInfo]:
        """Parse Solana transaction"""
        try:
            meta = result.get("meta", {})
            message = result.get("transaction", {}).get("message", {})

            pre = meta.get("preBalances", [])
            post = meta.get("postBalances", [])
            amount = Decimal(abs(post[0] - pre[0]) if post and pre else 0) / Decimal(
                10**self.network_config.decimals
            )

            return PaymentInfo(
                transaction_id=result.get("transaction", {}).get("signatures", [""])[0]
                if result.get("transaction")
                else "",
                wallet_address=message.get("accountKeys", [""])[0],
                amount=amount,
                currency=self.currency_symbol,
                status=PaymentStatus.CONFIRMED
                if meta.get("err") is None
                else PaymentStatus.FAILED,
                timestamp=datetime.fromtimestamp(result.get("blockTime", 0)),
                block_height=result.get("slot"),
                confirmations=0,
                fee=Decimal(meta.get("fee", 0))
                / Decimal(10**self.network_config.decimals),
                from_address=message.get("accountKeys", [""])[0]
                if message.get("accountKeys")
                else "",
                to_address=message.get("accountKeys", ["", ""])[1]
                if len(message.get("accountKeys", [])) > 1
                else "",
                raw_data=result,
            )
        except Exception:
            return None
