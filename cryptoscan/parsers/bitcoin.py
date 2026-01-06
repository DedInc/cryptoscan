"""
Bitcoin chain parser using RPC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from ..models import PaymentInfo, PaymentStatus
from .base import ChainParser


class BitcoinParser(ChainParser):
    """Parser for Bitcoin transactions using RPC."""

    async def get_transactions(
        self, address: str, limit: int, expected_amount: Optional[Decimal] = None
    ) -> List[PaymentInfo]:
        """Get Bitcoin transactions via RPC"""
        await self.client.connect()

        try:
            # Use Bitcoin RPC methods
            # scantxoutset can scan for unspent outputs matching the address
            await self.client.call(
                "scantxoutset",
                ["start", [f"addr({address})"]],
            )
            # Note: Bitcoin RPC has limited transaction history access
            # For full transaction history, users should use block explorers or indexers
            return []
        except Exception:
            return []

    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get Bitcoin transaction via RPC"""
        await self.client.connect()

        try:
            tx = await self.client.call("getrawtransaction", [tx_id, True])
            if not tx:
                return None
            return self.parse_transaction(tx)
        except Exception:
            return None

    def parse_transaction(self, tx: dict, address: str = None) -> PaymentInfo:
        """Parse Bitcoin RPC transaction"""
        amount = Decimal(0)
        to_addr = ""

        # Parse vout for receiving amounts
        for vout in tx.get("vout", []):
            value = Decimal(vout.get("value", 0))
            amount += value
            if vout.get("scriptPubKey", {}).get("addresses"):
                to_addr = vout["scriptPubKey"]["addresses"][0]

        from_addr = ""
        if tx.get("vin") and tx["vin"]:
            if "coinbase" in tx["vin"][0]:
                from_addr = "<coinbase>"
            elif tx["vin"][0].get("txid"):
                from_addr = "<unknown>"

        return PaymentInfo(
            transaction_id=tx.get("txid", ""),
            wallet_address=to_addr,
            amount=amount,
            currency=self.currency_symbol,
            status=PaymentStatus.CONFIRMED
            if tx.get("confirmations", 0) > 0
            else PaymentStatus.PENDING,
            timestamp=datetime.fromtimestamp(tx.get("time", 0))
            if tx.get("time")
            else datetime.now(timezone.utc),
            block_height=tx.get("blockheight"),
            confirmations=tx.get("confirmations", 0),
            fee=None,
            from_address=from_addr,
            to_address=to_addr,
            raw_data=tx,
        )
