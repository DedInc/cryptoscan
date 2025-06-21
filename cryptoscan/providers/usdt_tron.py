"""
USDT Tron (TRC-20) Network Provider for CryptoScan

Implements USDT TRC-20 token monitoring using the tokenview.io API.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging

from ..core.base import BaseNetworkProvider, NetworkConfig, PaymentInfo, PaymentStatus
from ..exceptions import NetworkError, ProviderError


logger = logging.getLogger(__name__)


class USDTTronProvider(BaseNetworkProvider):
    """
    USDT Tron (TRC-20) network provider for monitoring USDT payments.
    
    Uses the tokenview.io API to fetch transaction data and monitor
    wallet addresses for incoming USDT payments on the Tron network.
    """
    
    # USDT TRC-20 constants
    USDT_DECIMALS = 6  # USDT has 6 decimal places
    UNITS_PER_USDT = 10**6  # 1 USDT = 1,000,000 smallest units
    USDT_CONTRACT_ADDRESS = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    
    def __init__(self, config: Optional[NetworkConfig] = None):
        """
        Initialize USDT Tron provider.

        Args:
            config: Network configuration. If None, uses default USDT Tron config.
        """
        if config is None:
            from ..config import default_config
            config = default_config.get_network_config("usdt_tron")

        super().__init__(config)

        # USDT Tron-specific request tracking
        self._request_count = 0
        self._last_request_time = 0
    
    @property
    def currency_symbol(self) -> str:
        """Return the currency symbol."""
        return "USDT"
    
    @property
    def network_name(self) -> str:
        """Return the network name."""
        return "USDT Tron (TRC-20)"
    
    @property
    def smallest_unit_name(self) -> str:
        """Return the smallest unit name."""
        return "micro-USDT"
    
    @property
    def units_per_token(self) -> int:
        """Return how many smallest units make up one USDT."""
        return self.UNITS_PER_USDT

    async def validate_wallet_address(self, address: str) -> bool:
        """
        Validate if a wallet address is valid for Tron network.
        
        Args:
            address: The wallet address to validate
            
        Returns:
            True if address is valid, False otherwise
        """
        if not address or not isinstance(address, str):
            return False
        
        # Tron addresses start with 'T' and are 34 characters long
        if not address.startswith('T') or len(address) != 34:
            return False
        
        # Check for valid base58 characters (Tron uses base58 encoding)
        tron_pattern = r'^T[A-HJ-NP-Za-km-z1-9]{33}$'
        if not re.match(tron_pattern, address):
            return False
        
        return True

    async def get_recent_transactions(self, wallet_address: str,
                                    limit: int = 10) -> List[PaymentInfo]:
        """
        Get recent USDT transactions for a Tron wallet address.

        Args:
            wallet_address: The wallet address to monitor
            limit: Maximum number of transactions to return

        Returns:
            List of PaymentInfo objects for recent USDT transactions
        """
        logger.debug(f"Getting recent USDT transactions for {wallet_address[:16]}...")

        try:
            # Build API URL for USDT transactions
            # Format: https://usdt.tokenview.io/api/usdt/addresstxlist/{address}/1/{limit}
            url = f"{self.config.rpc_url}addresstxlist/{wallet_address}/1/{limit}"

            # Use base class HTTP/2 client with proxy support
            logger.debug(f"Making HTTP/2 request to {url}")
            response = await self._make_request("GET", url)

            logger.debug(f"Response status: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text
                raise NetworkError(
                    f"Failed to get recent transactions: HTTP {response.status_code}",
                    response.status_code,
                    error_text
                )

            data = response.json()
            logger.debug(f"API response: {data}")

            # Check for API errors
            if data.get("code") != 1:
                error_msg = data.get("enMsg", "Unknown error")
                raise NetworkError(f"USDT Tron API error: {error_msg}")

            # Parse transactions
            transactions = []
            tx_list = data.get("data", {}).get("txs", [])
            
            for tx_data in tx_list:
                payment_info = self._parse_transaction(tx_data, wallet_address)
                if payment_info:
                    transactions.append(payment_info)

            logger.debug(f"Parsed {len(transactions)} USDT transactions")
            return transactions

        except Exception as e:
            logger.error(f"Failed to get recent transactions: {e}")
            raise ProviderError(f"Failed to get recent transactions: {e}", "USDT_TRON", e)

    async def get_transaction_details(self, transaction_id: str) -> Optional[PaymentInfo]:
        """
        Get detailed information about a specific USDT transaction.
        
        Args:
            transaction_id: The transaction ID/hash to look up
            
        Returns:
            PaymentInfo object if transaction exists, None otherwise
        """
        try:
            # For individual transaction details, we can use the same API
            # but we'll need to search through recent transactions
            # This is a limitation of the tokenview.io API structure
            logger.debug(f"Getting transaction details for {transaction_id}")
            
            # Note: tokenview.io doesn't have a direct transaction lookup endpoint
            # for USDT, so we return None and rely on get_recent_transactions
            return None

        except Exception as e:
            logger.error(f"Failed to get transaction details: {e}")
            raise ProviderError(f"Failed to get transaction details: {e}", "USDT_TRON", e)

    def _parse_transaction(self, tx_data: Dict[str, Any], wallet_address: str) -> Optional[PaymentInfo]:
        """
        Parse a transaction from the API response.
        
        Args:
            tx_data: Transaction data from API
            wallet_address: The wallet address being monitored
            
        Returns:
            PaymentInfo object or None if parsing fails
        """
        try:
            # Extract transaction details
            transaction_hash = tx_data.get("txid", "")
            from_address = tx_data.get("from", "")
            to_address = tx_data.get("to", "")
            value_str = tx_data.get("value", "0")
            timestamp_unix = tx_data.get("time", 0)
            block_height = tx_data.get("block_no", 0)
            confirmations = tx_data.get("confirmations", 0)
            token_contract = tx_data.get("token", "")

            # Verify this is a USDT transaction
            if token_contract != self.USDT_CONTRACT_ADDRESS:
                logger.debug(f"Skipping non-USDT transaction: {token_contract}")
                return None

            # Only process incoming transactions
            if to_address.lower() != wallet_address.lower():
                logger.debug(f"Skipping outgoing transaction to {to_address}")
                return None

            # Convert value from smallest units to USDT
            try:
                value_units = int(value_str)
                amount_usdt = self.convert_to_main_unit(value_units)
            except (ValueError, TypeError):
                logger.error(f"Invalid value format: {value_str}")
                return None

            # Convert timestamp
            timestamp = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc)

            # Determine payment status based on confirmations
            if confirmations >= 1:
                payment_status = PaymentStatus.CONFIRMED
            else:
                payment_status = PaymentStatus.PENDING

            logger.debug(f"Parsed USDT transaction: {amount_usdt} USDT to {wallet_address[:16]}")

            return PaymentInfo(
                transaction_id=transaction_hash,
                wallet_address=wallet_address,
                amount=amount_usdt,
                currency=self.currency_symbol,
                status=payment_status,
                timestamp=timestamp,
                block_height=block_height,
                confirmations=confirmations,
                fee=None,  # Fee information not provided by this API
                from_address=from_address,
                to_address=to_address,
                raw_data=tx_data
            )

        except Exception as e:
            logger.error(f"Failed to parse USDT transaction: {e}")
            return None
