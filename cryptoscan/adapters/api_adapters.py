"""API adapters for non-standard blockchain APIs"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import httpx

from ..models import PaymentInfo, PaymentStatus

logger = logging.getLogger(__name__)


class BaseAdapter:
    """Base class for API adapters"""

    def __init__(self, rpc_url: str, network_config):
        self.rpc_url = rpc_url
        self.network_config = network_config
        self.http_client: Optional[httpx.AsyncClient] = None

    async def connect(self):
        """Initialize HTTP client"""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(timeout=30.0, http2=True)

    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def get_transactions(self, address: str, limit: int = 10):
        """Get transactions - must be implemented by subclass"""
        raise NotImplementedError

    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get single transaction - must be implemented by subclass"""
        raise NotImplementedError


class TONCenterAdapter(BaseAdapter):
    """Adapter for TON Center API"""

    async def get_transactions(
        self, address: str, limit: int = 10
    ) -> List[PaymentInfo]:
        """Get transactions from TON Center API"""
        await self.connect()

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
            data = response.json()

            if "result" not in data:
                return []

            transactions = []
            for tx in data["result"]:
                parsed = self._parse_ton_tx(tx, address)
                if parsed:
                    transactions.append(parsed)

            return transactions
        except Exception as e:
            logger.error(f"TON API Error: {e}")
            return []

    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get single transaction"""
        await self.connect()

        try:
            response = await self.http_client.post(
                self.rpc_url,
                json={
                    "id": 1,
                    "jsonrpc": "2.0",
                    "method": "getTransaction",
                    "params": {"hash": tx_id},
                },
            )
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


class TRONGridAdapter(BaseAdapter):
    """Adapter for TRON Grid API"""

    async def get_transactions(
        self, address: str, limit: int = 10
    ) -> List[PaymentInfo]:
        """Get transactions from TRON Grid API"""
        await self.connect()

        try:
            # TRON uses REST API, not JSON-RPC
            response = await self.http_client.get(
                f"{self.rpc_url}/v1/accounts/{address}/transactions",
                params={"limit": limit},
            )
            data = response.json()

            transactions = []
            for tx in data.get("data", [])[:limit]:
                parsed = self._parse_tron_tx(tx, address)
                if parsed:
                    transactions.append(parsed)

            return transactions
        except Exception as e:
            logger.error(f"TRON API Error: {e}")
            return []

    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get single transaction"""
        await self.connect()

        try:
            response = await self.http_client.get(
                f"{self.rpc_url}/wallet/gettransactionbyid", params={"value": tx_id}
            )
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


# Registry of available adapters
ADAPTERS = {
    "ton_center": TONCenterAdapter,
    "tron_grid": TRONGridAdapter,
}


def get_adapter(
    adapter_name: str, rpc_url: str, network_config
) -> Optional[BaseAdapter]:
    """Get adapter instance by name"""
    adapter_class = ADAPTERS.get(adapter_name)
    if adapter_class:
        return adapter_class(rpc_url, network_config)
    return None
