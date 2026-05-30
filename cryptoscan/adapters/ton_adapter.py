"""TON Center API adapter."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx

__all__ = ["TONCenterAdapter"]

from ..core.exceptions import AdapterError
from ..core.models import PaymentInfo, PaymentStatus
from .base import MAX_RESPONSE_SIZE, BaseAdapter

logger = logging.getLogger(__name__)


class TONCenterAdapter(BaseAdapter):
    """Adapter for TON Center API"""

    async def get_transactions(
        self, address: str, limit: int = 10
    ) -> list[PaymentInfo]:
        """Get transactions from TON Center API with tenacity retry"""
        await self.connect()

        async for attempt in self._get_retry_context():
            with attempt:
                try:
                    # Use getTransactions method
                    response = await self.http_client.post(
                        self.rpc_url,
                        json={
                            "id": 1,
                            "jsonrpc": "2.0",
                            "method": "getTransactions",
                            "params": {"address": address, "limit": limit},
                        },
                    )
                    response.raise_for_status()

                    # Validate content type
                    content_type = response.headers.get("content-type", "")
                    if "application/json" not in content_type:
                        raise AdapterError(
                            f"Unexpected response content type: {content_type}",
                            adapter_name="ton_center",
                        )

                    # Check response size to prevent memory exhaustion
                    content_length = int(response.headers.get("content-length", 0))
                    if content_length > MAX_RESPONSE_SIZE:
                        raise AdapterError(
                            f"Response too large: {content_length} bytes",
                            adapter_name="ton_center",
                        )

                    data = response.json()

                    if "result" not in data:
                        return []

                    transactions = []
                    for tx in data["result"]:
                        parsed = self._parse_ton_tx(tx, address)
                        if parsed:
                            transactions.append(parsed)

                    return transactions

                except httpx.HTTPError as e:
                    logger.warning(
                        "TON Center API error: %s status=%s",
                        e.__class__.__name__,
                        getattr(e, "response", None) and e.response.status_code,
                    )
                    raise

                except AdapterError:
                    raise

                except (
                    KeyError,
                    ValueError,
                    TypeError,
                    IndexError,
                    ArithmeticError,
                ) as e:
                    logger.error(f"TON API Error: {e.__class__.__name__}")
                    raise AdapterError(
                        f"TON API error: {e.__class__.__name__}",
                        adapter_name="ton_center",
                        original_error=e,
                    ) from e

    async def get_transaction(self, tx_id: str) -> PaymentInfo | None:
        """Get single transaction with tenacity retry"""
        await self.connect()

        try:
            async for attempt in self._get_retry_context():
                with attempt:
                    response = await self.http_client.post(
                        self.rpc_url,
                        json={
                            "id": 1,
                            "jsonrpc": "2.0",
                            "method": "getTransaction",
                            "params": {"hash": tx_id},
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    if "result" not in data:
                        return None

                    return self._parse_ton_tx(data["result"])
        except httpx.HTTPError as e:
            logger.warning(
                "TON Center API error: %s status=%s",
                e.__class__.__name__,
                getattr(e, "response", None) and e.response.status_code,
            )
            return None
        except (AdapterError, KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to get TON transaction: {e.__class__.__name__}")
            return None

    def _parse_ton_tx(self, tx: dict, _address: str = None) -> PaymentInfo | None:
        """Parse TON transaction"""
        try:
            # TON has complex transaction structure
            in_msg = tx.get("in_msg", {})
            # out_msgs available in tx.get("out_msgs", []) if needed

            # Get value from incoming message
            value = int(in_msg.get("value", "0"))
            amount = Decimal(value) / Decimal(10**self.network_config.decimals)

            # Extract addresses
            source = in_msg.get("source", "")
            destination = in_msg.get("destination", "")

            return PaymentInfo(
                transaction_id=tx.get("transaction_id", {}).get("hash", ""),
                wallet_address=destination,
                amount=amount,
                currency=self.network_config.symbol,
                status=PaymentStatus.CONFIRMED,
                timestamp=datetime.fromtimestamp(tx.get("utime", 0), tz=timezone.utc),
                block_height=None,
                confirmations=1,
                fee=Decimal(tx.get("fee", "0"))
                / Decimal(10**self.network_config.decimals),
                from_address=source,
                to_address=destination,
                raw_data=tx,
            )
        except (KeyError, ValueError, TypeError, IndexError, ArithmeticError) as e:
            logger.error(f"TON TX Parse Error: {e}")
            return None
