"""
Bitcoin chain parser using RPC.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

__all__ = ["BitcoinParser"]

from ..core.exceptions import CSConnectionError, CSTimeoutError, RPCError
from ..core.models import PaymentInfo, PaymentStatus, TokenConfig
from .base import ChainParser

logger = logging.getLogger(__name__)


class BitcoinParser(ChainParser):
    """Parser for Bitcoin transactions using RPC."""

    async def get_block_number(self) -> int:
        return 0

    async def get_block_for_payment(
        self,
        _block_identifier: str,
        _wallet_address: str,
        _expected_amount: Decimal | None,
        _latest_block_num: int | None = None,
        _match_mode: object | None = None,
        _token_contract: str | TokenConfig | None = None,
    ) -> PaymentInfo | None:
        return None

    async def get_transactions(
        self,
        address: str,
        _limit: int,
        _expected_amount: Decimal | None = None,
        _match_mode: object | None = None,
        _token_contract: str | TokenConfig | None = None,
    ) -> list[PaymentInfo]:
        """Get Bitcoin transactions via RPC"""
        await self.client.connect()

        try:
            await self.client.call(
                "scantxoutset",
                ["start", [f"addr({address})"]],
            )
            return []
        except (RPCError, CSConnectionError, CSTimeoutError) as e:
            logger.warning(
                f"Bitcoin get_transactions network error for {address}: "
                f"{e.__class__.__name__}"
            )
            return []
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(
                f"Bitcoin get_transactions failed for {address}: {e.__class__.__name__}"
            )
            return []

    async def get_transaction(self, tx_id: str) -> PaymentInfo | None:
        """Get Bitcoin transaction via RPC"""
        await self.client.connect()

        try:
            tx = await self.client.call("getrawtransaction", [tx_id, True])
            if not tx:
                return None
            return self.parse_transaction(tx)
        except (RPCError, CSConnectionError, CSTimeoutError) as e:
            logger.warning(
                f"Failed to fetch Bitcoin transaction {tx_id}: {e.__class__.__name__}"
            )
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(
                f"Failed to parse Bitcoin transaction {tx_id}: {e.__class__.__name__}"
            )
            return None

    def parse_transaction(self, tx: dict, _address: str = None) -> PaymentInfo:
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
            timestamp=datetime.fromtimestamp(tx.get("time", 0), tz=timezone.utc)
            if tx.get("time")
            else datetime.now(timezone.utc),
            block_height=tx.get("blockheight"),
            confirmations=tx.get("confirmations", 0),
            fee=None,
            from_address=from_addr,
            to_address=to_addr,
            raw_data=tx,
        )
