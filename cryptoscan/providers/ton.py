"""
TON Network Provider for CryptoScan

Implements TON blockchain monitoring using the tonscan.com API.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging

from ..core.base import BaseNetworkProvider, NetworkConfig, PaymentInfo, PaymentStatus
from ..exceptions import NetworkError, ProviderError


logger = logging.getLogger(__name__)


class TONProvider(BaseNetworkProvider):
    """
    TON network provider for monitoring TON payments.
    
    Uses the tonscan.com API to fetch transaction data and monitor
    wallet addresses for incoming payments.
    """
    
    # TON constants
    NANOTONS_PER_TON = 10**9
    
    def __init__(self, config: Optional[NetworkConfig] = None):
        """
        Initialize TON provider.

        Args:
            config: Network configuration. If None, uses default TON config.
        """
        if config is None:
            from ..config import default_config
            config = default_config.get_network_config("ton")

        super().__init__(config)

        # TON-specific request tracking
        self._request_count = 0
        self._last_request_time = 0

        # Note: HTTP/2 client is now handled by the base class
    
    @property
    def currency_symbol(self) -> str:
        """Return the currency symbol."""
        return "TON"
    
    @property
    def network_name(self) -> str:
        """Return the network name."""
        return "TON"
    
    @property
    def smallest_unit_name(self) -> str:
        """Return the smallest unit name."""
        return "nanotons"
    
    @property
    def units_per_token(self) -> int:
        """Return how many nanotons make up one TON."""
        return self.NANOTONS_PER_TON

    async def validate_wallet_address(self, address: str) -> bool:
        """
        Validate if a wallet address is valid for TON.
        
        TON addresses can be in different formats:
        - Raw format: starts with UQ or EQ, followed by base64-like characters
        - User-friendly format: similar but with different encoding
        
        Args:
            address: The wallet address to validate
            
        Returns:
            True if address appears valid, False otherwise
        """
        if not address or not isinstance(address, str):
            return False
        
        # Check for TON address format
        # TON addresses typically start with UQ, EQ, or kQ and are 48 characters long
        if len(address) != 48:
            return False
        
        # Check for valid prefixes
        if not (address.startswith('UQ') or address.startswith('EQ') or address.startswith('kQ')):
            return False
        
        # Check for valid base64-like characters after prefix
        # TON addresses use base64url encoding with some modifications
        ton_pattern = r'^[UEk]Q[A-Za-z0-9_-]{46}$'
        if not re.match(ton_pattern, address):
            return False
        
        return True

    async def get_recent_transactions(self, wallet_address: str,
                                    limit: int = 10) -> List[PaymentInfo]:
        """
        Get recent transactions for a TON wallet address.

        Args:
            wallet_address: The wallet address to monitor
            limit: Maximum number of transactions to return

        Returns:
            List of PaymentInfo objects for recent transactions
        """
        logger.debug(f"Getting recent transactions for {wallet_address[:16]}...")

        try:
            # Build API URL for TON transactions
            url = f"{self.config.rpc_url}getTransactionsForAddress"
            params = {
                "address": wallet_address,
                "limit": limit
            }

            # Use base class HTTP/2 client with proxy support
            logger.debug(f"Making HTTP/2 request to {url}")
            response = await self._make_request(
                "GET",
                url,
                params=params
            )

            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            if response.status_code != 200:
                error_text = response.text
                raise NetworkError(
                    f"Failed to get recent transactions: HTTP {response.status_code}",
                    response.status_code,
                    error_text
                )

            # Parse JSON response
            try:
                data = response.json()
                logger.debug(f"Successfully parsed JSON response")
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Response content: {response.text[:500]}...")
                raise NetworkError(f"Invalid JSON response: {e}")

            # Check for API errors - the response is wrapped in a "json" object
            json_data = data.get("json", {})
            if json_data.get("status") != "success":
                error_info = json_data.get("error", "Unknown error")
                raise NetworkError(f"TON API error: {error_info}")

            # Parse transactions
            transactions = []
            tx_list = json_data.get("data", {}).get("transactions", [])

            for tx_data in tx_list:
                try:
                    payment_info = self._parse_transaction(tx_data, wallet_address)
                    if payment_info:
                        transactions.append(payment_info)
                except Exception as e:
                    logger.warning(f"Failed to parse transaction: {e}")
                    continue

            logger.debug(f"Found {len(transactions)} valid transactions")
            return transactions

        except Exception as e:
            logger.error(f"Failed to get recent transactions: {e}")
            raise ProviderError(f"Failed to get recent transactions: {e}", "TON", e)

    async def get_transaction_details(self, transaction_id: str) -> Optional[PaymentInfo]:
        """
        Get detailed information about a specific TON transaction.

        Args:
            transaction_id: The transaction hash to look up

        Returns:
            PaymentInfo object if transaction exists, None otherwise
        """
        try:
            # Build API URL for specific transaction
            url = f"{self.config.rpc_url}getTransaction"
            params = {
                "hash": transaction_id
            }

            # Use base class HTTP/2 client with proxy support
            response = await self._make_request(
                "GET",
                url,
                params=params
            )

            if response.status_code != 200:
                error_text = response.text
                raise NetworkError(
                    f"Failed to get transaction details: HTTP {response.status_code}",
                    response.status_code,
                    error_text
                )

            # Parse JSON response
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise NetworkError(f"Invalid JSON response: {e}")

            # Check for API errors - the response is wrapped in a "json" object
            json_data = data.get("json", {})
            if json_data.get("status") != "success":
                error_info = json_data.get("error", "Unknown error")
                raise NetworkError(f"TON API error: {error_info}")

            # Parse transaction
            tx_data = json_data.get("data")
            if not tx_data:
                return None

            # Use the account address as the wallet address for parsing
            wallet_address = tx_data.get("account", "")
            return self._parse_transaction(tx_data, wallet_address)

        except Exception as e:
            logger.error(f"Failed to get transaction details: {e}")
            raise ProviderError(f"Failed to get transaction details: {e}", "TON", e)

    def _parse_transaction(self, tx_data: Dict[str, Any], wallet_address: str) -> Optional[PaymentInfo]:
        """Parse TON transaction data into PaymentInfo."""
        try:
            # Extract basic transaction info
            transaction_hash = tx_data.get("hash")
            account = tx_data.get("account")
            utime = tx_data.get("utime")
            fee = tx_data.get("fee")

            # Get incoming message data
            in_msg = tx_data.get("in_msg", {})

            if not transaction_hash:
                logger.debug("Missing transaction hash")
                return None

            # Check if this is an incoming transaction
            if not in_msg or in_msg.get("direction") != "in":
                logger.debug(f"Transaction {transaction_hash[:16]} is not incoming")
                return None

            # Get the value from incoming message
            value = in_msg.get("value", 0)

            # Skip transactions with zero value
            if not value or value <= 0:
                logger.debug(f"Transaction {transaction_hash[:16]} has zero or negative value: {value}")
                return None

            # Convert value from nanotons to TON
            amount_ton = self.convert_to_main_unit(value)

            # Validate amount is positive
            if amount_ton <= 0:
                logger.debug(f"Invalid amount: {amount_ton}")
                return None

            # Determine transaction status
            # TON transactions in the API are typically confirmed if they appear
            payment_status = PaymentStatus.CONFIRMED

            # Check for failed transactions based on exit codes
            compute_exit_code = tx_data.get("compute_exit_code")
            action_result_code = tx_data.get("action_result_code")

            if (compute_exit_code is not None and compute_exit_code != 0) or \
               (action_result_code is not None and action_result_code != 0):
                payment_status = PaymentStatus.FAILED

            # Convert fee if available
            fee_ton = None
            if fee:
                try:
                    fee_ton = self.convert_to_main_unit(fee)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse fee '{fee}': {e}")

            # Convert timestamp
            if utime:
                try:
                    timestamp = datetime.fromtimestamp(utime, tz=timezone.utc)
                except (ValueError, OSError) as e:
                    logger.warning(f"Invalid timestamp {utime}: {e}")
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            # Get addresses
            from_address = in_msg.get("source")
            to_address = in_msg.get("destination", account)

            # Validate that this transaction is for the monitored wallet
            if to_address and to_address != wallet_address:
                logger.debug(f"Transaction to {to_address} doesn't match wallet {wallet_address}")
                wallet_address = to_address

            logger.debug(f"Parsed TON transaction: {amount_ton} TON to {wallet_address[:16]}")

            return PaymentInfo(
                transaction_id=transaction_hash,
                wallet_address=wallet_address,
                amount=amount_ton,
                currency=self.currency_symbol,
                status=payment_status,
                timestamp=timestamp,
                block_height=None,  # TON uses logical time instead of block height
                confirmations=1,
                fee=fee_ton,
                from_address=from_address,
                to_address=to_address,
                raw_data=tx_data
            )

        except Exception as e:
            logger.error(f"Failed to parse TON transaction: {e}")
            return None
