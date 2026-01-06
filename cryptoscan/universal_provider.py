"""Universal blockchain provider for ALL networks"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Optional, Union

from .config import UserConfig
from .models import PaymentInfo
from .networks import NetworkConfig, get_network
from .rpc_client import RPCClient
from .adapters import get_adapter
from .chain_parsers import EVMParser, SolanaParser, BitcoinParser

logger = logging.getLogger(__name__)

# Type alias for parser types
ParserType = Union[EVMParser, SolanaParser, BitcoinParser, None]


class UniversalProvider:
    """
    Universal provider that works with ANY blockchain
    Dynamically adapts to network type (EVM, Solana, Cosmos, etc.)
    """

    def __init__(
        self,
        network: str | NetworkConfig,
        rpc_url: Optional[str] = None,
        user_config: Optional[UserConfig] = None,
    ):
        # Get network config
        if isinstance(network, str):
            self.network_config = get_network(network)
            if not self.network_config:
                raise ValueError(f"Unknown network: {network}")
        else:
            self.network_config = network

        # Use custom RPC or default
        self.rpc_url = rpc_url or self.network_config.rpc_url
        self.config = user_config or UserConfig()

        # Check if network has custom API adapter
        self.api_adapter = None
        if self.network_config.api_adapter:
            self.api_adapter = get_adapter(
                self.network_config.api_adapter, self.rpc_url, self.network_config
            )

        self.client = RPCClient(self.rpc_url, self.config)
        self._parser = self._create_parser()

    @property
    def NETWORK_NAME(self) -> str:
        """Get network name"""
        return self.network_config.name

    @property
    def CURRENCY_SYMBOL(self) -> str:
        """Get currency symbol"""
        return self.network_config.symbol

    async def connect(self):
        """Connect to RPC"""
        await self.client.connect()

    async def close(self):
        """Close connections"""
        await self.client.close()
        if self.api_adapter:
            await self.api_adapter.close()

    def _create_parser(self) -> ParserType:
        """Create appropriate parser for chain type.

        Returns:
            Parser instance appropriate for the network's chain type,
            or None if no parser is available for the chain type.
        """
        chain_type = self.network_config.chain_type

        if chain_type == "evm":
            return EVMParser(self.client, self.network_config, self.CURRENCY_SYMBOL)
        elif chain_type == "solana":
            return SolanaParser(self.client, self.network_config, self.CURRENCY_SYMBOL)
        elif chain_type == "bitcoin":
            return BitcoinParser(self.client, self.network_config, self.CURRENCY_SYMBOL)
        elif chain_type == "tron":
            return EVMParser(
                self.client, self.network_config, self.CURRENCY_SYMBOL
            )  # TRON uses EVM-compatible calls
        else:
            return None

    async def validate_wallet_address(self, address: str) -> bool:
        """Validate wallet address format"""
        return self.network_config.validate_address(address)

    async def get_recent_transactions(
        self, wallet_address: str, limit: int = 10
    ) -> List[PaymentInfo]:
        """Get recent transactions"""
        if self.api_adapter:
            return await self.api_adapter.get_transactions(wallet_address, limit)

        if self._parser and hasattr(self._parser, "get_transactions"):
            return await self._parser.get_transactions(wallet_address, limit)

        return []

    async def get_transaction_details(
        self, transaction_id: str
    ) -> Optional[PaymentInfo]:
        """Get transaction details"""
        if self.api_adapter:
            return await self.api_adapter.get_transaction(transaction_id)

        if self._parser and hasattr(self._parser, "get_transaction"):
            return await self._parser.get_transaction(transaction_id)

        return None

    async def find_payment(
        self, wallet_address: str, expected_amount: Decimal, max_transactions: int = 10
    ) -> Optional[PaymentInfo]:
        """Find payment matching expected amount.

        Args:
            wallet_address: The wallet address to search for payments
            expected_amount: The exact amount to match
            max_transactions: Maximum number of transactions to check

        Returns:
            PaymentInfo if a matching payment is found, None otherwise
        """
        # For EVM parser, pass expected_amount for early match
        if self._parser and hasattr(self._parser, "get_transactions"):
            try:
                # Try to call with expected_amount parameter
                transactions = await self._parser.get_transactions(
                    wallet_address, max_transactions, expected_amount=expected_amount
                )
            except TypeError:
                # Fallback for parsers that don't support expected_amount
                transactions = await self._parser.get_transactions(
                    wallet_address, max_transactions
                )
        elif self.api_adapter:
            transactions = await self.api_adapter.get_transactions(
                wallet_address, max_transactions
            )
        else:
            transactions = []

        logger.info(
            f"Got {len(transactions)} transactions, checking for amount {expected_amount}"
        )

        for tx in transactions:
            tx_normalized = tx.amount.normalize()
            expected_normalized = expected_amount.normalize()
            logger.debug(
                f"TX {tx.transaction_id[:16]}... amount={tx_normalized} vs expected={expected_normalized}"
            )

            if tx_normalized == expected_normalized:
                logger.info(f"Payment found: {tx.transaction_id}")
                return tx

        return None

    def _parse_evm_tx(
        self,
        tx: dict,
        block: dict = None,
        receipt: dict = None,
        latest_block_num: int = None,
    ) -> PaymentInfo:
        """Parse EVM transaction using the shared parser.

        This method delegates to the EVMParser to avoid code duplication.
        The parser handles all EVM-specific parsing logic.

        Args:
            tx: Transaction data dictionary
            block: Optional block data dictionary
            receipt: Optional transaction receipt dictionary
            latest_block_num: Optional latest block number for confirmation calculation

        Returns:
            PaymentInfo with parsed transaction data

        Raises:
            NotImplementedError: If no EVM parser is available
        """
        if self._parser and hasattr(self._parser, "parse_transaction"):
            return self._parser.parse_transaction(
                tx, block, receipt, latest_block_num=latest_block_num
            )
        raise NotImplementedError("EVM parser not available")

    def __repr__(self):
        return f"UniversalProvider(network={self.NETWORK_NAME}, type={self.network_config.chain_type}, rpc={self.rpc_url})"
