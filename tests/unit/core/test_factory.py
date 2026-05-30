import pytest

from cryptoscan.core.exceptions import ValidationError
from cryptoscan.factory import (
    _should_use_realtime,
    create_monitor,
    get_provider,
    get_supported_networks,
)
from cryptoscan.monitoring import PaymentMonitor
from cryptoscan.networks import NetworkConfig, register_common_networks
from cryptoscan.provider.universal_provider import UniversalProvider


@pytest.fixture(autouse=True)
def _register_networks() -> None:
    register_common_networks()


def test_create_monitor_valid(ethereum_config: NetworkConfig) -> None:
    monitor = create_monitor(
        network=ethereum_config,
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
        expected_amount="1.0",
    )
    assert isinstance(monitor, PaymentMonitor)


def test_create_monitor_unknown_network_no_rpc() -> None:
    with pytest.raises(ValidationError):
        create_monitor(
            network="nonexistent_chain",
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
            expected_amount="1.0",
        )


def test_create_monitor_invalid_address(ethereum_config: NetworkConfig) -> None:
    with pytest.raises(ValidationError):
        create_monitor(
            network=ethereum_config,
            wallet_address="not_a_valid_address",
            expected_amount="1.0",
        )


def test_create_monitor_negative_amount(ethereum_config: NetworkConfig) -> None:
    with pytest.raises(ValidationError):
        create_monitor(
            network=ethereum_config,
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
            expected_amount="-1.0",
        )


def test_get_provider_valid() -> None:
    provider = get_provider("ethereum")
    assert isinstance(provider, UniversalProvider)


def test_get_provider_nonexistent() -> None:
    with pytest.raises(ValidationError):
        get_provider("nonexistent_network")


def test_get_supported_networks() -> None:
    networks = get_supported_networks()
    assert "ethereum" in networks


def test_should_use_realtime_with_ws(ethereum_config: NetworkConfig) -> None:
    assert _should_use_realtime(ethereum_config) is True


def test_should_use_realtime_without_ws(bitcoin_config: NetworkConfig) -> None:
    assert _should_use_realtime(bitcoin_config) is False
