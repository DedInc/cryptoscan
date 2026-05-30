"""Private helpers for factory.create_monitor (orchestration-only entry point)."""

from __future__ import annotations

import logging
from dataclasses import replace
from decimal import Decimal

from .core.config import UserConfig
from .core.exceptions import ValidationError
from .core.models import MatchMode, TokenConfig
from .networks import NetworkConfig, get_network
from .networks import list_networks as get_network_list

__all__: list[str] = []

logger = logging.getLogger(__name__)


def _should_use_realtime(
    network_config: NetworkConfig, custom_rpc_url: str | None = None
) -> bool:
    """Detect if real-time monitoring should be used based on WebSocket availability."""
    if custom_rpc_url and custom_rpc_url.startswith("wss://"):
        return True
    return network_config.ws_url is not None


def _resolve_network_config(
    network: str | NetworkConfig,
    rpc_url: str | None,
    ws_url: str | None,
) -> NetworkConfig:
    """Resolve a ``NetworkConfig`` from a name, direct object, or custom URL."""
    if isinstance(network, NetworkConfig):
        return network

    if isinstance(network, str):
        config = get_network(network)
        if config:
            return config
        if not rpc_url:
            supported = ", ".join(get_network_list())
            raise ValidationError(
                f"Network '{network}' not in registry. "
                f"Either add it to NETWORKS or provide rpc_url parameter.\n"
                f"Registered networks: {supported}"
            )
        logger.warning(
            f"No registered network for '{network}', assuming EVM chain type"
        )
        return NetworkConfig(
            name=network,
            symbol="",
            rpc_url=rpc_url,
            ws_url=ws_url,
            chain_type="evm",
        )

    raise ValidationError(f"Invalid network parameter type: {type(network)}")


def _override_network_urls(
    config: NetworkConfig,
    rpc_url: str | None,
    ws_url: str | None,
) -> NetworkConfig:
    """Return a copy of *config* with custom URL overrides applied."""
    if not (rpc_url or ws_url):
        return config
    return replace(
        config,
        rpc_url=rpc_url or config.rpc_url,
        ws_url=ws_url if ws_url is not None else config.ws_url,
    )


def _resolve_match_mode(match_mode: MatchMode | str) -> MatchMode:
    """Normalise a ``MatchMode`` / string to a ``MatchMode`` enum value."""
    if isinstance(match_mode, MatchMode):
        return match_mode
    return MatchMode(match_mode)


def _validate_expected_amount(
    expected_amount: str | Decimal | None,
    resolved_match_mode: MatchMode,
) -> None:
    """Validate *expected_amount* against the resolved match mode."""
    if expected_amount is not None:
        amount = Decimal(str(expected_amount))
        if amount <= 0:
            raise ValidationError("Expected amount must be positive")
    elif resolved_match_mode != MatchMode.ANY:
        raise ValidationError(
            "expected_amount is required when match_mode is not 'any'"
        )


def _apply_user_config_overrides(
    user_config: UserConfig | None,
    timeout: float | None,
    max_retries: int | None,
) -> UserConfig:
    """Ensure a ``UserConfig`` exists and apply optional overrides."""
    if user_config is None:
        user_config = UserConfig()
    if timeout is not None:
        user_config.timeout = timeout
    if max_retries is not None:
        user_config.max_retries = max_retries
    return user_config


def _warn_on_string_token(token_contract: str | TokenConfig | None) -> None:
    """Warn when ``token_contract`` is a plain string (decimal mismatch risk)."""
    if isinstance(token_contract, str):
        logger.warning(
            "token_contract is passed as a string! The library will use native "
            "network decimals (usually 18). "
            "If you are tracking USDT/USDC, it will FAIL because they use 6 decimals. "
            "USE THIS INSTEAD: token_contract=TokenConfig("
            "contract_address='...', symbol='USDT', decimals=6)"
        )
