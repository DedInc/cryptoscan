"""
API Adapters module

Contains all API adapters for different blockchain networks and services.
Each adapter handles the specific API format and requirements of different networks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .base import BaseAdapter
from .ton_adapter import TONCenterAdapter
from .tron_adapter import TRONGridAdapter

if TYPE_CHECKING:
    from ..networks import NetworkConfig

# Registry of available adapters
ADAPTERS = {
    "ton_center": TONCenterAdapter,
    "tron_grid": TRONGridAdapter,
}


def get_adapter(
    adapter_name: str, rpc_url: str, network_config: "NetworkConfig"
) -> Optional[BaseAdapter]:
    """Get adapter instance by name"""
    adapter_class = ADAPTERS.get(adapter_name)
    if adapter_class:
        return adapter_class(rpc_url, network_config)
    return None


__all__ = [
    "BaseAdapter",
    "TONCenterAdapter",
    "TRONGridAdapter",
    "get_adapter",
    "ADAPTERS",
]
