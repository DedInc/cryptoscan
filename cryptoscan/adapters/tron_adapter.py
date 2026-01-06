"""TRON Grid API adapter."""

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


class TRONGridAdapter(BaseAdapter):
    """Adapter for TRON Grid API"""

    async def get_transactions(
        self, address: str, limit: int = 10
    ) -> List[PaymentInfo]:
        """Get transactions from TRON Grid API with tenacity retry"""
        await self.connect()

        async for attempt in self._get_retry_context():
            with attempt:
                try:
                    # TRON uses REST API, not JSON-RPC
                    response = await self.http_client.get(
                        f"{self.rpc_url}/v1/accounts/{address}/transactions",
                        params={"limit": limit},
                    )
                    response.raise_for_status()

                    # Validate content type
                    content_type = response.headers.get("content-type", "")
                    if "application/json" not in content_type:
                        raise AdapterError(
                            f"Unexpected response content type: {content_type}",
                            adapter_name="tron_grid",
                        )

                    # Check response size to prevent memory exhaustion
                    content_length = int(response.headers.get("content-length", 0))
                    if content_length > MAX_RESPONSE_SIZE:
                        raise AdapterError(
                            f"Response too large: {content_length} bytes",
                            adapter_name="tron_grid",
                        )

                    data = response.json()

                    transactions = []
                    for tx in data.get("data", [])[:limit]:
                        parsed = self._parse_tron_tx(tx, address)
                        if parsed:
                            transactions.append(parsed)

                    return transactions

                except httpx.HTTPError as e:
                    logger.warning(
                        f"TRON API HTTP Error (attempt {attempt.retry_state.attempt_number}): {e}"
                    )
                    raise  # Let tenacity handle retry

                except AdapterError:
                    raise  # Don't retry adapter errors

                except Exception as e:
                    logger.error(f"TRON API Error: {e}")
                    raise AdapterError(
                        f"TRON API error: {e}",
                        adapter_name="tron_grid",
                        original_error=e,
                    )

    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get single transaction with tenacity retry"""
        await self.connect()

        try:
            async for attempt in self._get_retry_context():
                with attempt:
                    response = await self.http_client.get(
                        f"{self.rpc_url}/wallet/gettransactionbyid",
                        params={"value": tx_id},
                    )
                    response.raise_for_status()
                    data = response.json()
                    return self._parse_tron_tx(data)
        except Exception as e:
            logger.error(f"Failed to get TRON transaction: {e}")
            return None

    def _parse_tron_tx(self, tx: dict, address: str = None) -> Optional[PaymentInfo]:
        """Parse TRON transaction"""
        try:
            raw_data = tx.get("raw_data", {})
            contract = raw_data.get("contract", [{}])[0]
            value_data = contract.get("parameter", {}).get("value", {})

            amount = Decimal(value_data.get("amount", 0)) / Decimal(
                10**self.network_config.decimals
            )

            return PaymentInfo(
                transaction_id=tx.get("txID", ""),
                wallet_address=value_data.get("to_address", ""),
                amount=amount,
                currency=self.network_config.symbol,
                status=PaymentStatus.CONFIRMED
                if tx.get("ret", [{}])[0].get("contractRet") == "SUCCESS"
                else PaymentStatus.FAILED,
                timestamp=datetime.fromtimestamp(raw_data.get("timestamp", 0) / 1000),
                block_height=tx.get("blockNumber"),
                confirmations=1,
                fee=None,
                from_address=value_data.get("owner_address", ""),
                to_address=value_data.get("to_address", ""),
                raw_data=tx,
            )
        except Exception as e:
            logger.error(f"TRON TX Parse Error: {e}")
            return None
