"""
Solana Network Provider for CryptoScan

Implements Solana blockchain monitoring using the Solana RPC API.
"""

import uuid
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import httpx
import logging

from ..core.base import BaseNetworkProvider, NetworkConfig, PaymentInfo, PaymentStatus
from ..exceptions import NetworkError, ProviderError


logger = logging.getLogger(__name__)


class SolanaProvider(BaseNetworkProvider):
    """
    Solana network provider for monitoring SOL payments.
    
    Uses the Solana RPC API to fetch transaction data and monitor
    wallet addresses for incoming payments.
    """
    
    # Solana constants
    LAMPORTS_PER_SOL = 1_000_000_000
    
    def __init__(self, config: Optional[NetworkConfig] = None):
        """
        Initialize Solana provider.

        Args:
            config: Network configuration. If None, uses default Solana config.
        """
        if config is None:
            from ..config import default_config
            config = default_config.get_network_config("solana")

        super().__init__(config)

        # Solana-specific request tracking
        self._request_count = 0
        self._last_request_time = 0
    
    @property
    def currency_symbol(self) -> str:
        """Return the currency symbol."""
        return "SOL"
    
    @property
    def network_name(self) -> str:
        """Return the network name."""
        return "Solana"
    
    @property
    def smallest_unit_name(self) -> str:
        """Return the smallest unit name."""
        return "lamports"
    
    @property
    def units_per_token(self) -> int:
        """Return how many lamports make up one SOL."""
        return self.LAMPORTS_PER_SOL
    
    async def validate_wallet_address(self, address: str) -> bool:
        """
        Validate if a wallet address is valid for Solana.
        
        Solana addresses are base58-encoded strings, typically 32-44 characters long.
        
        Args:
            address: The wallet address to validate
            
        Returns:
            True if address appears valid, False otherwise
        """
        if not address or not isinstance(address, str):
            return False
        
        # Basic length and character validation
        if len(address) < 32 or len(address) > 44:
            return False
        
        # Check for valid base58 characters
        base58_pattern = r'^[1-9A-HJ-NP-Za-km-z]+$'
        if not re.match(base58_pattern, address):
            return False
        
        return True
    
    async def get_recent_transactions(self, wallet_address: str,
                                    limit: int = 10) -> List[PaymentInfo]:
        """
        Get recent transactions for a Solana wallet address.

        Args:
            wallet_address: The wallet address to monitor
            limit: Maximum number of transactions to return

        Returns:
            List of PaymentInfo objects for recent transactions
        """
        logger.debug(f"Getting recent transactions for {wallet_address[:16]}...")

        try:
            # First, get transaction signatures
            signatures = await self._get_signatures(wallet_address, limit)

            if not signatures:
                return []

            # Get detailed transaction information
            transactions = []

            for sig_info in signatures:
                signature = sig_info.get("signature")
                if not signature:
                    continue

                try:
                    payment_info = await self.get_transaction_details(signature)
                    if payment_info and payment_info.wallet_address == wallet_address:
                        transactions.append(payment_info)
                except Exception as e:
                    logger.warning(f"Failed to get details for transaction {signature[:16]}: {e}")
                    continue

            return transactions

        except Exception as e:
            logger.error(f"Failed to get recent transactions: {e}")
            raise ProviderError(f"Failed to get recent transactions: {e}", "Solana", e)
    
    async def get_transaction_details(self, transaction_id: str) -> Optional[PaymentInfo]:
        """
        Get detailed information about a specific Solana transaction.

        Args:
            transaction_id: The transaction signature to look up

        Returns:
            PaymentInfo object if transaction exists, None otherwise
        """
        try:
            payload = {
                "method": "getTransaction",
                "jsonrpc": "2.0",
                "params": [
                    transaction_id,
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed",
                        "maxSupportedTransactionVersion": 0
                    }
                ],
                "id": str(uuid.uuid4())
            }

            # Use the enhanced request method with proxy support
            response = await self._make_request(
                "POST",
                self.config.rpc_url,
                json=payload
            )

            if response.status_code != 200:
                error_text = response.text
                raise NetworkError(
                    f"Failed to get transaction details: HTTP {response.status_code}",
                    response.status_code,
                    error_text
                )

            data = response.json()

            # Check for RPC errors
            if "error" in data:
                error_info = data["error"]
                raise NetworkError(f"Solana RPC error: {error_info}")

            result = data.get("result")
            if not result:
                return None

            return self._parse_transaction(result, transaction_id)

        except httpx.RequestError as e:
            logger.error(f"Network error getting transaction details: {e}")
            raise NetworkError(f"Network error getting transaction details: {e}")
        except Exception as e:
            logger.error(f"Failed to get transaction details: {e}")
            raise ProviderError(f"Failed to get transaction details: {e}", "Solana", e)
    
    async def _get_signatures(self, address: str, limit: int) -> List[Dict[str, Any]]:
        """Get recent transaction signatures for an address."""
        logger.debug(f"Requesting signatures for {address[:16]}...")

        try:
            payload = {
                "method": "getSignaturesForAddress",
                "jsonrpc": "2.0",
                "params": [address, {"limit": limit}],
                "id": str(uuid.uuid4())
            }

            response = await self._make_request(
                "POST",
                self.config.rpc_url,
                json=payload
            )

            if response.status_code != 200:
                error_text = response.text
                raise NetworkError(
                    f"Failed to get signatures: HTTP {response.status_code}",
                    response.status_code,
                    error_text
                )

            data = response.json()

            # Check for RPC errors
            if "error" in data:
                error_info = data["error"]
                raise NetworkError(f"Solana RPC error: {error_info}")

            # Get results
            result = data.get("result", [])
            successful_transactions = [tx for tx in result if tx.get("err") is None]

            logger.debug(f"Found {len(successful_transactions)} successful transactions")
            return successful_transactions

        except httpx.RequestError as e:
            logger.error(f"Network error getting signatures: {e}")
            raise NetworkError(f"Network error getting signatures: {e}")
    
    def _parse_transaction(self, tx_data: Dict[str, Any], transaction_id: str) -> Optional[PaymentInfo]:
        """Parse Solana transaction data into PaymentInfo."""
        try:
            meta = tx_data.get("meta", {})
            transaction = tx_data.get("transaction", {})
            message = transaction.get("message", {})

            if not meta or not message:
                return None

            # Extract basic info
            block_time = tx_data.get("blockTime")
            slot = tx_data.get("slot")
            transaction_error = meta.get("err")
            fee_lamports = meta.get("fee", 0)
            fee_sol = self.convert_to_main_unit(fee_lamports)

            # Get account keys
            account_keys = message.get("accountKeys", [])
            if not account_keys:
                return None

            # Analyze balance changes to find incoming payments
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])

            if len(pre_balances) != len(post_balances) or len(pre_balances) != len(account_keys):
                return None

            # Find the largest positive balance change (incoming payment)
            largest_incoming = None
            largest_change = 0

            for i, (pre, post, account) in enumerate(zip(pre_balances, post_balances, account_keys)):
                change = post - pre
                if change > largest_change:
                    largest_change = change
                    largest_incoming = {
                        "pubkey": account.get("pubkey"),
                        "change_lamports": change,
                        "change_sol": self.convert_to_main_unit(change)
                    }

            if not largest_incoming or largest_change <= 0:
                return None

            # Create PaymentInfo for the incoming payment
            wallet_address = largest_incoming["pubkey"]
            amount_sol = largest_incoming["change_sol"]
            timestamp = datetime.fromtimestamp(block_time) if block_time else datetime.now(timezone.utc)
            status = PaymentStatus.CONFIRMED if not transaction_error else PaymentStatus.FAILED

            return PaymentInfo(
                transaction_id=transaction_id,
                wallet_address=wallet_address,
                amount=amount_sol,
                currency=self.currency_symbol,
                status=status,
                timestamp=timestamp,
                block_height=slot,
                confirmations=1,
                fee=fee_sol,
                raw_data=tx_data
            )

        except Exception as e:
            logger.error(f"Failed to parse transaction {transaction_id}: {e}")
            return None
