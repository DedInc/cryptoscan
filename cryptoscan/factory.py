"""Factory functions for creating monitors and providers."""

from __future__ import annotations

import logging
from decimal import Decimal

from .core.config import UserConfig
from .core.exceptions import ValidationError
from .core.models import MatchMode, TokenConfig
from .factory_helpers import (
    _apply_user_config_overrides,
    _override_network_urls,
    _resolve_match_mode,
    _resolve_network_config,
    _should_use_realtime,
    _validate_expected_amount,
    _warn_on_string_token,
)
from .monitoring import PaymentMonitor
from .networks import NetworkConfig, get_network
from .networks import list_networks as get_network_list
from .provider.universal_provider import UniversalProvider

__all__ = ["create_monitor", "get_provider", "get_supported_networks"]

logger = logging.getLogger(__name__)


def create_monitor(
    network: str | NetworkConfig,
    wallet_address: str,
    expected_amount: str | Decimal | None = None,
    poll_interval: float = 15.0,
    max_transactions: int = 10,
    auto_stop: bool = False,
    rpc_url: str | None = None,
    ws_url: str | None = None,
    monitor_id: str | None = None,
    user_config: UserConfig | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
    realtime: bool | None = None,
    min_confirmations: int = 1,
    match_mode: MatchMode | str = MatchMode.EXACT,
    token_contract: str | TokenConfig | None = None,
) -> PaymentMonitor:
    """Create a payment monitor for any blockchain network.

    Accepts a registered network name, a ``NetworkConfig``, or any chain via
    ``rpc_url``/``ws_url``. Mode is auto-detected from WebSocket availability
    and can be forced with ``realtime``. ``match_mode`` controls amount
    matching (``"exact"``, ``"at_least"``, ``"any"``); ``expected_amount``
    is required unless mode is ``"any"``.

    Raises ValidationError on invalid network or parameters.

    Examples:
        >>> monitor = create_monitor("ethereum", "0x...", "1.0", auto_stop=True)
        >>> monitor = create_monitor("ethereum", "0x...", match_mode="any")
    """
    network_config = _resolve_network_config(network, rpc_url, ws_url)
    network_config = _override_network_urls(network_config, rpc_url, ws_url)
    resolved_match_mode = _resolve_match_mode(match_mode)
    _validate_expected_amount(expected_amount, resolved_match_mode)
    user_config = _apply_user_config_overrides(user_config, timeout, max_retries)

    provider = UniversalProvider(
        network=network_config,
        rpc_url=None,
        user_config=user_config,
    )

    if not network_config.validate_address(wallet_address):
        raise ValidationError(
            f"Invalid {network_config.name} address format: {wallet_address}"
        )

    _warn_on_string_token(token_contract)

    if realtime is None:
        realtime = _should_use_realtime(network_config, rpc_url)

    return PaymentMonitor(
        provider=provider,
        wallet_address=wallet_address,
        expected_amount=expected_amount,
        poll_interval=poll_interval,
        max_transactions=max_transactions,
        auto_stop=auto_stop,
        monitor_id=monitor_id,
        user_config=user_config,
        realtime=realtime,
        min_confirmations=min_confirmations,
        match_mode=resolved_match_mode,
        token_contract=token_contract,
    )


def get_supported_networks() -> list[str]:
    """Get list of all supported network names.

    Returns:
        List of all available network identifiers (including aliases)
    """
    return get_network_list()


def get_provider(
    network: str,
    rpc_url: str | None = None,
    user_config: UserConfig | None = None,
) -> UniversalProvider:
    """Get a universal provider instance for ANY network.

    Args:
        network: Network name or alias
        rpc_url: Optional custom RPC URL
        user_config: Optional user configuration

    Returns:
        UniversalProvider instance that works with any blockchain

    Raises:
        ValidationError: If network not supported
    """
    network_config = get_network(network)
    if not network_config:
        supported = ", ".join(get_network_list())
        raise ValidationError(
            f"Unsupported network: '{network}'. Supported networks: {supported}"
        )

    return UniversalProvider(
        network=network_config, rpc_url=rpc_url, user_config=user_config
    )
