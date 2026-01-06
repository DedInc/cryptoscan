"""TON Center API adapter."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import httpx

from ..exceptions import AdapterError
from ..models import PaymentInfo, PaymentStatus
from .base import MAX_RESPONSE_SIZE, BaseAdapter

logger = logging.getLogger(__name__)


class TONCenterAdapter(BaseAdapter):
    """Adapter for TON Center API"""

    async def get_transactions(
        self, address: str, limit: int = 10
    ) -> List[PaymentInfo]:
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
                        f"TON API HTTP Error (attempt {attempt.retry_state.attempt_number}): {e}"
                    )
                    raise  # Let tenacity handle retry

                except AdapterError:
                    raise  # Don't retry adapter errors

                except Exception as e:
                    logger.error(f"TON API Error: {e}")
                    raise AdapterError(
                        f"TON API error: {e}",
                        adapter_name="ton_center",
                        original_error=e,
                    )

    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
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
        except Exception as e:
            logger.error(f"Failed to get TON transaction: {e}")
            return None

    def _parse_ton_tx(self, tx: dict, address: str = None) -> Optional[PaymentInfo]:
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
                timestamp=datetime.fromtimestamp(tx.get("utime", 0)),
                block_height=None,
                confirmations=1,
                fee=Decimal(tx.get("fee", "0"))
                / Decimal(10**self.network_config.decimals),
                from_address=source,
                to_address=destination,
                raw_data=tx,
            )
        except Exception as e:
            logger.error(f"TON TX Parse Error: {e}")
            return None
