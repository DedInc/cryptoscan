"""
Ethereum Network Provider for CryptoScan

Implements Ethereum blockchain monitoring using the ethvm.dev GraphQL API.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging

from ..core.base import BaseNetworkProvider, NetworkConfig, PaymentInfo, PaymentStatus
from ..exceptions import NetworkError, ProviderError


logger = logging.getLogger(__name__)


class EthereumProvider(BaseNetworkProvider):
    """
    Ethereum network provider for monitoring ETH payments.
    
    Uses the ethvm.dev GraphQL API to fetch transaction data and monitor
    wallet addresses for incoming payments.
    """
    
    # Ethereum constants
    WEI_PER_ETH = 10**18
    
    def __init__(self, config: Optional[NetworkConfig] = None):
        """
        Initialize Ethereum provider.

        Args:
            config: Network configuration. If None, uses default Ethereum config.
        """
        if config is None:
            from ..config import default_config
            config = default_config.get_network_config("ethereum")

        super().__init__(config)

        # Ethereum-specific request tracking
        self._request_count = 0
        self._last_request_time = 0

        # Note: HTTP/2 client is now handled by the base class
    
    @property
    def currency_symbol(self) -> str:
        """Return the currency symbol."""
        return "ETH"
    
    @property
    def network_name(self) -> str:
        """Return the network name."""
        return "Ethereum"
    
    @property
    def smallest_unit_name(self) -> str:
        """Return the smallest unit name."""
        return "wei"
    
    @property
    def units_per_token(self) -> int:
        """Return how many wei make up one ETH."""
        return self.WEI_PER_ETH


    
    async def validate_wallet_address(self, address: str) -> bool:
        """
        Validate if a wallet address is valid for Ethereum.
        
        Ethereum addresses are hex strings starting with 0x, 42 characters total.
        
        Args:
            address: The wallet address to validate
            
        Returns:
            True if address appears valid, False otherwise
        """
        if not address or not isinstance(address, str):
            return False
        
        # Check format: 0x followed by 40 hex characters
        if len(address) != 42:
            return False
        
        if not address.startswith('0x'):
            return False
        
        # Check for valid hex characters after 0x
        hex_pattern = r'^0x[0-9a-fA-F]{40}$'
        if not re.match(hex_pattern, address):
            return False
        
        return True
    
    async def get_recent_transactions(self, wallet_address: str,
                                    limit: int = 10) -> List[PaymentInfo]:
        """
        Get recent transactions for an Ethereum wallet address.

        Args:
            wallet_address: The wallet address to monitor
            limit: Maximum number of transactions to return

        Returns:
            List of PaymentInfo objects for recent transactions
        """
        logger.debug(f"Getting recent transactions for {wallet_address[:16]}...")

        try:
            # GraphQL query for incoming ETH transfers
            query = """
            query getEthTransactionTransfers($direction: TransferDirection, $hash: String!, $_limit: Int, $_nextKey: String) {
              getEthTransactionTransfers(
                owner: $hash
                direction: $direction
                limit: $_limit
                nextKey: $_nextKey
              ) {
                transfers {
                  ...TxsTransfers
                  __typename
                }
                nextKey
                __typename
              }
            }

            fragment TxsTransfers on ETHTransactionTransfer {
              transfer {
                ...Transfers
                __typename
              }
              stateDiff {
                to {
                  ...BalanceFragment
                  __typename
                }
                from {
                  ...BalanceFragment
                  __typename
                }
                __typename
              }
              transactionStateDiff {
                to {
                  ...BalanceFragment
                  __typename
                }
                from {
                  ...BalanceFragment
                  __typename
                }
                __typename
              }
              value
              __typename
            }

            fragment Transfers on Transfer {
              type
              subtype
              transactionHash
              block
              timestamp
              from
              to
              txFee
              status
              __typename
            }

            fragment BalanceFragment on BalanceDiff {
              before
              after
              __typename
            }
            """

            payload = {
                "operationName": "getEthTransactionTransfers",
                "variables": {
                    "direction": "INCOMING",
                    "hash": wallet_address,
                    "_limit": limit
                },
                "query": query
            }

            # Use base class HTTP/2 client with proxy support
            logger.debug(f"Making HTTP/2 request to {self.config.rpc_url}")
            response = await self._make_request(
                "POST",
                self.config.rpc_url,
                json=payload
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

            # Check for GraphQL errors
            if "errors" in data:
                error_info = data["errors"]
                raise NetworkError(f"Ethereum GraphQL error: {error_info}")

            # Parse transactions
            transactions = []
            transfers = data.get("data", {}).get("getEthTransactionTransfers", {}).get("transfers", [])

            for transfer_data in transfers:
                try:
                    payment_info = self._parse_transaction(transfer_data, wallet_address)
                    if payment_info:
                        transactions.append(payment_info)
                except Exception as e:
                    logger.warning(f"Failed to parse transfer: {e}")
                    continue

            logger.debug(f"Found {len(transactions)} valid transactions")
            return transactions

        except Exception as e:
            logger.error(f"Failed to get recent transactions: {e}")
            raise ProviderError(f"Failed to get recent transactions: {e}", "Ethereum", e)
    
    async def get_transaction_details(self, transaction_id: str) -> Optional[PaymentInfo]:
        """
        Get detailed information about a specific Ethereum transaction.

        Args:
            transaction_id: The transaction hash to look up

        Returns:
            PaymentInfo object if transaction exists, None otherwise
        """
        try:
            # GraphQL query for specific transaction details
            query = """
            query getEthTransactionByHash($hash: String!) {
              getEthTransactionByHash(hash: $hash) {
                hash
                block
                timestamp
                from
                to
                value
                txFee
                status
                __typename
              }
            }
            """

            payload = {
                "operationName": "getEthTransactionByHash",
                "variables": {
                    "hash": transaction_id
                },
                "query": query
            }

            # Use base class HTTP/2 client with proxy support
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

            # Parse JSON response
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise NetworkError(f"Invalid JSON response: {e}")

            # Check for GraphQL errors
            if "errors" in data:
                error_info = data["errors"]
                raise NetworkError(f"Ethereum GraphQL error: {error_info}")

            # Parse transaction
            tx_data = data.get("data", {}).get("getEthTransactionByHash")
            if not tx_data:
                return None

            # Convert to transfer format for parsing
            transfer_data = {
                "transfer": {
                    "transactionHash": tx_data.get("hash"),
                    "block": tx_data.get("block"),
                    "timestamp": tx_data.get("timestamp"),
                    "from": tx_data.get("from"),
                    "to": tx_data.get("to"),
                    "txFee": tx_data.get("txFee"),
                    "status": tx_data.get("status")
                },
                "value": tx_data.get("value")
            }

            # Use the to address as the wallet address for parsing
            wallet_address = tx_data.get("to", "")
            return self._parse_transaction(transfer_data, wallet_address)

        except Exception as e:
            logger.error(f"Failed to get transaction details: {e}")
            raise ProviderError(f"Failed to get transaction details: {e}", "Ethereum", e)
    
    def _parse_transaction(self, transfer_data: Dict[str, Any], wallet_address: str) -> Optional[PaymentInfo]:
        """Parse Ethereum transfer data into PaymentInfo."""
        try:
            transfer = transfer_data.get("transfer", {})
            value_hex = transfer_data.get("value")

            if not transfer or not value_hex:
                logger.debug("Missing transfer data or value")
                return None

            # Extract basic info
            transaction_hash = transfer.get("transactionHash")
            block_number = transfer.get("block")
            timestamp_unix = transfer.get("timestamp")
            from_address = transfer.get("from")
            to_address = transfer.get("to")
            status = transfer.get("status")
            tx_fee_hex = transfer.get("txFee")

            if not transaction_hash:
                logger.debug("Missing transaction hash")
                return None

            # Status validation - must be explicitly True for confirmed payments
            if status is not True:
                logger.debug(f"Transaction {transaction_hash[:16]} has status: {status}")
                # Still parse failed transactions but mark them as failed
                payment_status = PaymentStatus.FAILED
            else:
                payment_status = PaymentStatus.CONFIRMED

            # Convert hex values to decimal with better error handling
            try:
                # Handle different hex formats
                if isinstance(value_hex, str):
                    if value_hex.startswith('0x'):
                        value_wei = int(value_hex, 16)
                    else:
                        value_wei = int(value_hex, 16)
                else:
                    value_wei = int(value_hex)

                amount_eth = self.convert_to_main_unit(value_wei)

                # Validate amount is positive
                if amount_eth <= 0:
                    logger.debug(f"Invalid amount: {amount_eth}")
                    return None

            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse value '{value_hex}': {e}")
                return None

            # Convert fee if available
            fee_eth = None
            if tx_fee_hex:
                try:
                    if isinstance(tx_fee_hex, str):
                        if tx_fee_hex.startswith('0x'):
                            fee_wei = int(tx_fee_hex, 16)
                        else:
                            fee_wei = int(tx_fee_hex, 16)
                    else:
                        fee_wei = int(tx_fee_hex)
                    fee_eth = self.convert_to_main_unit(fee_wei)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse fee '{tx_fee_hex}': {e}")

            # Convert timestamp with validation
            if timestamp_unix:
                try:
                    timestamp = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc)
                except (ValueError, OSError) as e:
                    logger.warning(f"Invalid timestamp {timestamp_unix}: {e}")
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            # Validate addresses
            if to_address and to_address.lower() != wallet_address.lower():
                logger.debug(f"Transaction to {to_address} doesn't match wallet {wallet_address}")
                wallet_address = to_address

            logger.debug(f"Parsed ETH transaction: {amount_eth} ETH to {wallet_address[:16]}")

            return PaymentInfo(
                transaction_id=transaction_hash,
                wallet_address=wallet_address,
                amount=amount_eth,
                currency=self.currency_symbol,
                status=payment_status,
                timestamp=timestamp,
                block_height=block_number,
                confirmations=1,
                fee=fee_eth,
                from_address=from_address,
                to_address=to_address,
                raw_data=transfer_data
            )

        except Exception as e:
            logger.error(f"Failed to parse Ethereum transaction: {e}")
            return None
