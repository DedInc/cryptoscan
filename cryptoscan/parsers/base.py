"""
Base chain parser abstract class.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from decimal import Decimal
from typing import TYPE_CHECKING, TypeVar

from ..core.models import MatchMode, PaymentInfo, TokenConfig

if TYPE_CHECKING:
    from ..networks import NetworkConfig
    from ..rpc.client import RPCClient

__all__ = ["ChainParser"]

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ChainParser(ABC):
    """Abstract base class for chain-specific parsers."""

    def __init__(
        self, client: RPCClient, network_config: NetworkConfig, currency_symbol: str
    ) -> None:
        self.client = client
        self.network_config = network_config
        self.currency_symbol = currency_symbol

    @staticmethod
    async def safe_parse(
        coro: Awaitable[T],
        context: str = "parsing",
        default: T | None = None,
        catch: tuple[type[Exception], ...] = (
            KeyError,
            ValueError,
            TypeError,
            IndexError,
            ArithmeticError,
        ),
    ) -> T | None:
        try:
            return await coro
        except catch as e:
            logger.warning(f"Error during {context}: {e.__class__.__name__}: {e!r}")
            return default

    @abstractmethod
    async def get_transactions(
        self,
        address: str,
        limit: int,
        expected_amount: Decimal | None = None,
        match_mode: MatchMode | None = None,
        token_contract: str | TokenConfig | None = None,
    ) -> list[PaymentInfo]:
        """Get transactions for an address."""
        ...

    @abstractmethod
    async def get_transaction(self, tx_id: str) -> PaymentInfo | None:
        """Get a single transaction by ID."""
        ...

    @abstractmethod
    async def get_block_number(self) -> int:
        """Return the current/latest block number for this chain."""
        ...

    @abstractmethod
    async def get_block_for_payment(
        self,
        block_identifier: str,
        wallet_address: str,
        expected_amount: Decimal | None,
        latest_block_num: int | None = None,
        match_mode: MatchMode | None = None,
        token_contract: str | TokenConfig | None = None,
    ) -> PaymentInfo | None:
        """Fetch a block by identifier, scan its transactions for a payment
        to wallet_address matching expected_amount.
        Return PaymentInfo if found, None otherwise.

        Args:
            block_identifier: Chain-specific block identifier (e.g. block hash for EVM)
            wallet_address: Target wallet address to match
            expected_amount: Expected payment amount to match (None for mode=ANY)
            latest_block_num: Optional latest block number for confirmation calculation
            match_mode: Amount comparison strategy (exact, at_least, any)
            token_contract: Optional ERC-20 token contract address or TokenConfig
                to scan logs for
        """
        ...
