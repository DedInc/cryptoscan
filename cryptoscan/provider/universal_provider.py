"""Universal blockchain provider for ALL networks"""

from __future__ import annotations

import logging
from decimal import Decimal

from ..adapters import get_adapter
from ..core.config import UserConfig
from ..core.models import MatchMode, PaymentInfo, TokenConfig, match_amount
from ..networks import NetworkConfig, get_network
from ..parsers import BitcoinParser, ChainParser, EVMParser, SolanaParser
from ..parsers.evm import _resolve_token_address
from ..rpc.client import RPCClient
from ..security import mask_transaction_id, mask_url

__all__ = ["UniversalProvider", "amounts_match", "register_parser", "PARSER_REGISTRY"]

logger = logging.getLogger(__name__)

ParserType = EVMParser | SolanaParser | BitcoinParser | None

PARSER_REGISTRY: dict[str, type[ChainParser]] = {
    "evm": EVMParser,
    "solana": SolanaParser,
    "bitcoin": BitcoinParser,
    "tron": EVMParser,
}


def register_parser(chain_type: str, parser_class: type[ChainParser]) -> None:
    PARSER_REGISTRY[chain_type] = parser_class


def amounts_match(actual: Decimal, expected: Decimal) -> bool:
    return actual.normalize() == expected.normalize()


class UniversalProvider:
    """
    Universal provider that works with ANY blockchain
    Dynamically adapts to network type (EVM, Solana, Cosmos, etc.)
    """

    def __init__(
        self,
        network: str | NetworkConfig,
        rpc_url: str | None = None,
        user_config: UserConfig | None = None,
    ) -> None:
        if isinstance(network, str):
            self.network_config = get_network(network)
            if not self.network_config:
                raise ValueError(f"Unknown network: {network}")
        else:
            self.network_config = network

        self.rpc_url = rpc_url or self.network_config.rpc_url
        self.config = user_config or UserConfig()

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

    async def connect(self) -> None:
        """Connect to RPC"""
        await self.client.connect()

    async def close(self) -> None:
        """Close connections"""
        await self.client.close()
        if self.api_adapter:
            await self.api_adapter.close()

    def _create_parser(self) -> ParserType:
        chain_type = self.network_config.chain_type
        parser_class = PARSER_REGISTRY.get(chain_type)
        if parser_class is not None:
            return parser_class(self.client, self.network_config, self.CURRENCY_SYMBOL)
        logger.warning(f"No parser registered for chain type: {chain_type!r}")
        return None

    async def validate_wallet_address(self, address: str) -> bool:
        """Validate wallet address format"""
        return self.network_config.validate_address(address)

    async def get_recent_transactions(
        self, wallet_address: str, limit: int = 10
    ) -> list[PaymentInfo]:
        """Get recent transactions"""
        if self.api_adapter:
            return await self.api_adapter.get_transactions(wallet_address, limit)

        if self._parser and hasattr(self._parser, "get_transactions"):
            return await self._parser.get_transactions(wallet_address, limit)

        return []

    async def get_transaction_details(self, transaction_id: str) -> PaymentInfo | None:
        """Get transaction details"""
        if self.api_adapter:
            return await self.api_adapter.get_transaction(transaction_id)

        if self._parser and hasattr(self._parser, "get_transaction"):
            return await self._parser.get_transaction(transaction_id)

        return None

    async def find_payment(
        self,
        wallet_address: str,
        expected_amount: Decimal | None,
        max_transactions: int = 10,
        match_mode: MatchMode = MatchMode.EXACT,
        token_contract: str | TokenConfig | None = None,
    ) -> PaymentInfo | None:
        """Find payment matching expected amount.

        Args:
            wallet_address: The wallet address to search for payments
            expected_amount: The amount to match (None for MatchMode.ANY)
            max_transactions: Maximum number of transactions to check
            match_mode: How to compare amounts (exact, at_least, any)
            token_contract: Optional ERC-20 token contract address to scan

        Returns:
            PaymentInfo if a matching payment is found, None otherwise
        """
        if self._parser and hasattr(self._parser, "get_transactions"):
            try:
                transactions = await self._parser.get_transactions(
                    wallet_address,
                    max_transactions,
                    expected_amount=expected_amount,
                    match_mode=match_mode,
                    token_contract=token_contract,
                )
            except TypeError:
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
            "Got %s transactions, checking for amount %s (mode=%s)",
            len(transactions),
            expected_amount,
            match_mode.value,
        )

        token_addr = _resolve_token_address(token_contract)

        for tx in transactions:
            logger.debug(
                "TX %s amount=%s vs expected=%s (mode=%s)",
                mask_transaction_id(tx.transaction_id),
                tx.amount,
                expected_amount,
                match_mode.value,
            )

            if match_amount(tx.amount, expected_amount, match_mode):
                if token_addr and tx.token_contract.lower() != token_addr.lower():
                    continue
                logger.info(f"Payment found: {mask_transaction_id(tx.transaction_id)}")
                return tx

        return None

    async def get_block_number(self) -> int:
        """Get current block number via parser."""
        if self._parser:
            return await self._parser.get_block_number()
        raise NotImplementedError("No parser available for this chain")

    async def get_block_for_payment(
        self,
        block_identifier: str,
        wallet_address: str,
        expected_amount: Decimal | None,
        latest_block_num: int | None = None,
        match_mode: MatchMode = MatchMode.EXACT,
        token_contract: str | TokenConfig | None = None,
    ) -> PaymentInfo | None:
        """Fetch a block and check for matching payment via parser."""
        if self._parser:
            return await self._parser.get_block_for_payment(
                block_identifier,
                wallet_address,
                expected_amount,
                latest_block_num,
                match_mode=match_mode,
                token_contract=token_contract,
            )
        raise NotImplementedError("No parser available for this chain")

    def __repr__(self) -> str:
        return (
            f"UniversalProvider("
            f"network={self.NETWORK_NAME}, "
            f"type={self.network_config.chain_type}, "
            f"rpc={mask_url(self.rpc_url)})"
        )
