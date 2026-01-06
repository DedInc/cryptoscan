"""
Base chain parser abstract class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from ..models import PaymentInfo

if TYPE_CHECKING:
    from ..networks import NetworkConfig
    from ..rpc_client import RPCClient


class ChainParser(ABC):
    """Abstract base class for chain-specific parsers."""

    def __init__(
        self, client: "RPCClient", network_config: "NetworkConfig", currency_symbol: str
    ) -> None:
        self.client = client
        self.network_config = network_config
        self.currency_symbol = currency_symbol

    @abstractmethod
    async def get_transactions(
        self, address: str, limit: int, expected_amount: Optional[Decimal] = None
    ) -> List[PaymentInfo]:
        """Get transactions for an address."""
        ...

    @abstractmethod
    async def get_transaction(self, tx_id: str) -> Optional[PaymentInfo]:
        """Get a single transaction by ID."""
        ...
