"""
Bitcoin Network Provider for CryptoScan

Implements Bitcoin blockchain monitoring using the blockchain.info Haskoin Store API.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging

from ..core.base import BaseNetworkProvider, NetworkConfig, PaymentInfo, PaymentStatus
from ..exceptions import NetworkError, ProviderError


logger = logging.getLogger(__name__)


class BitcoinProvider(BaseNetworkProvider):
    """
    Bitcoin network provider for monitoring BTC payments.
    
    Uses the blockchain.info Haskoin Store API to fetch transaction data and monitor
    wallet addresses for incoming payments.
    """
    
    # Bitcoin constants
    SATOSHIS_PER_BTC = 100_000_000  # 1 BTC = 100,000,000 satoshis
    
    def __init__(self, config: Optional[NetworkConfig] = None):
        """
        Initialize Bitcoin provider.

        Args:
            config: Network configuration. If None, uses default Bitcoin config.
        """
        if config is None:
            from ..config import default_config
            config = default_config.get_network_config("bitcoin")

        super().__init__(config)

        # Bitcoin-specific request tracking
        self._request_count = 0
        self._last_request_time = 0
    
    @property
    def currency_symbol(self) -> str:
        """Return the currency symbol."""
        return "BTC"
    
    @property
    def network_name(self) -> str:
        """Return the network name."""
        return "Bitcoin"
    
    @property
    def smallest_unit_name(self) -> str:
        """Return the smallest unit name."""
        return "satoshis"
    
    @property
    def units_per_token(self) -> int:
        """Return how many smallest units make up one BTC."""
        return self.SATOSHIS_PER_BTC

    async def validate_wallet_address(self, address: str) -> bool:
        """
        Validate if a wallet address is valid for Bitcoin network.
        
        Args:
            address: The wallet address to validate
            
        Returns:
            True if address is valid, False otherwise
        """
        if not address or not isinstance(address, str):
            return False
        
        # Bitcoin address patterns
        # Legacy addresses (P2PKH): start with '1', 26-35 characters
        # Script addresses (P2SH): start with '3', 26-35 characters  
        # Bech32 addresses (P2WPKH/P2WSH): start with 'bc1', 42+ characters
        
        # Legacy P2PKH addresses
        if re.match(r'^1[A-HJ-NP-Za-km-z1-9]{25,34}$', address):
            return True
        
        # P2SH addresses
        if re.match(r'^3[A-HJ-NP-Za-km-z1-9]{25,34}$', address):
            return True
        
        # Bech32 addresses (native SegWit)
        if re.match(r'^bc1[a-z0-9]{39,59}$', address):
            return True
        
        return False

    async def get_recent_transactions(self, wallet_address: str,
                                    limit: int = 10) -> List[PaymentInfo]:
        """
        Get recent transactions for a Bitcoin wallet address.

        Args:
            wallet_address: The wallet address to monitor
            limit: Maximum number of transactions to return

        Returns:
            List of PaymentInfo objects for recent Bitcoin transactions
        """
        logger.debug(f"Getting recent transactions for {wallet_address[:16]}...")

        try:
            # Build API URL for Bitcoin transactions
            # Format: https://api.blockchain.info/haskoin-store/btc/address/{address}/transactions?limit={limit}&offset=0
            url = f"{self.config.rpc_url}address/{wallet_address}/transactions"
            params = {
                "limit": limit,
                "offset": 0
            }

            # Use base class HTTP/2 client with proxy support
            logger.debug(f"Making HTTP/2 request to {url}")
            response = await self._make_request("GET", url, params=params)

            logger.debug(f"Response status: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text
                raise NetworkError(
                    f"Failed to get recent transactions: HTTP {response.status_code}",
                    response.status_code,
                    error_text
                )

            data = response.json()
            logger.debug(f"API response: Found {len(data)} transactions")

            # Parse transactions - we need to get full transaction details for each
            transactions = []
            for tx_summary in data:
                txid = tx_summary.get("txid")
                if txid:
                    # Get full transaction details
                    tx_details = await self.get_transaction_details(txid)
                    if tx_details and tx_details.wallet_address.lower() == wallet_address.lower():
                        transactions.append(tx_details)

            logger.debug(f"Parsed {len(transactions)} Bitcoin transactions")
            return transactions

        except Exception as e:
            logger.error(f"Failed to get recent transactions: {e}")
            raise ProviderError(f"Failed to get recent transactions: {e}", "BITCOIN", e)

    async def get_transaction_details(self, transaction_id: str) -> Optional[PaymentInfo]:
        """
        Get detailed information about a specific Bitcoin transaction.
        
        Args:
            transaction_id: The transaction ID/hash to look up
            
        Returns:
            PaymentInfo object if transaction exists, None otherwise
        """
        try:
            # Build API URL for specific transaction
            # Format: https://api.blockchain.info/haskoin-store/btc/transaction/{txid}
            url = f"{self.config.rpc_url}transaction/{transaction_id}"

            logger.debug(f"Getting transaction details for {transaction_id}")
            response = await self._make_request("GET", url)

            if response.status_code != 200:
                error_text = response.text
                raise NetworkError(
                    f"Failed to get transaction details: HTTP {response.status_code}",
                    response.status_code,
                    error_text
                )

            data = response.json()
            logger.debug(f"Transaction details received for {transaction_id}")

            # Parse the transaction to find incoming payments
            return self._parse_transaction(data)

        except Exception as e:
            logger.error(f"Failed to get transaction details: {e}")
            raise ProviderError(f"Failed to get transaction details: {e}", "BITCOIN", e)

    def _parse_transaction(self, tx_data: Dict[str, Any]) -> Optional[PaymentInfo]:
        """
        Parse a transaction from the API response.
        
        Args:
            tx_data: Transaction data from API
            
        Returns:
            PaymentInfo object or None if parsing fails
        """
        try:
            # Extract transaction details
            transaction_hash = tx_data.get("txid", "")
            timestamp_unix = tx_data.get("time", 0)
            block_info = tx_data.get("block", {})
            block_height = block_info.get("height", 0) if block_info else 0
            fee_satoshis = tx_data.get("fee", 0)
            
            # Convert timestamp
            timestamp = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc) if timestamp_unix else None

            # Convert fee from satoshis to BTC
            fee_btc = self.convert_to_main_unit(fee_satoshis) if fee_satoshis else None

            # Look through outputs to find incoming payments
            outputs = tx_data.get("outputs", [])
            inputs = tx_data.get("inputs", [])
            
            # Get sender address from first input (simplified)
            from_address = ""
            if inputs and len(inputs) > 0:
                from_address = inputs[0].get("address", "")

            # Process each output to find incoming payments
            for output in outputs:
                to_address = output.get("address", "")
                value_satoshis = output.get("value", 0)
                
                if value_satoshis > 0:
                    # Convert value from satoshis to BTC
                    amount_btc = self.convert_to_main_unit(value_satoshis)

                    # Determine payment status - if block height exists, it's confirmed
                    payment_status = PaymentStatus.CONFIRMED if block_height > 0 else PaymentStatus.PENDING

                    logger.debug(f"Parsed Bitcoin transaction: {amount_btc} BTC to {to_address[:16]}")

                    return PaymentInfo(
                        transaction_id=transaction_hash,
                        wallet_address=to_address,
                        amount=amount_btc,
                        currency=self.currency_symbol,
                        status=payment_status,
                        timestamp=timestamp,
                        block_height=block_height,
                        confirmations=1 if block_height > 0 else 0,
                        fee=fee_btc,
                        from_address=from_address,
                        to_address=to_address,
                        raw_data=tx_data
                    )

            return None

        except Exception as e:
            logger.error(f"Failed to parse Bitcoin transaction: {e}")
            return None
