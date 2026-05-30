from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from cryptoscan.networks import (
    NetworkConfig,
    _networks_lock,
    _registered_networks,
    create_network_config,
    get_network,
    list_networks,
    register_network,
)


@pytest.fixture
def sample_config() -> NetworkConfig:
    return NetworkConfig(
        name="Ethereum",
        symbol="ETH",
        rpc_url="https://ethereum-rpc.publicnode.com",
        ws_url="wss://ethereum-rpc.publicnode.com",
        address_pattern=r"^0x[a-fA-F0-9]{40}$",
        decimals=18,
        aliases=["eth", "ether"],
        chain_type="evm",
    )


class TestRegisterNetwork:
    def test_register_and_retrieve_by_name(self, sample_config: NetworkConfig) -> None:
        register_network(sample_config)
        result = get_network("ethereum")
        assert result is sample_config

    def test_register_lowercases_key(self, sample_config: NetworkConfig) -> None:
        register_network(sample_config)
        with _networks_lock:
            assert "ethereum" in _registered_networks


class TestGetNetwork:
    def test_find_by_name_case_insensitive(self, sample_config: NetworkConfig) -> None:
        register_network(sample_config)
        assert get_network("ETHEREUM") is sample_config
        assert get_network("Ethereum") is sample_config
        assert get_network("ethereum") is sample_config

    def test_find_by_alias(self, sample_config: NetworkConfig) -> None:
        register_network(sample_config)
        assert get_network("eth") is sample_config
        assert get_network("ether") is sample_config

    def test_find_by_alias_case_insensitive(self, sample_config: NetworkConfig) -> None:
        register_network(sample_config)
        assert get_network("ETH") is sample_config

    def test_returns_none_for_unknown(self) -> None:
        assert get_network("nonexistent_network") is None

    def test_strips_whitespace(self, sample_config: NetworkConfig) -> None:
        register_network(sample_config)
        assert get_network("  ethereum  ") is sample_config


class TestListNetworks:
    def test_returns_all_names_and_aliases_sorted(self) -> None:
        eth = NetworkConfig(
            name="ethereum",
            symbol="ETH",
            rpc_url="https://ethereum-rpc.publicnode.com",
            aliases=["eth"],
        )
        bsc = NetworkConfig(
            name="bsc",
            symbol="BNB",
            rpc_url="https://bsc-rpc.publicnode.com",
            aliases=["bnb", "binance"],
        )
        register_network(eth)
        register_network(bsc)

        result = list_networks()
        assert result == ["binance", "bnb", "bsc", "eth", "ethereum"]

    def test_empty_when_no_networks(self) -> None:
        assert list_networks() == []


class TestCreateNetworkConfig:
    def test_creates_valid_config(self) -> None:
        config = create_network_config(
            name="testnet",
            symbol="TST",
            rpc_url="https://test.example.com",
            ws_url="wss://test.example.com",
            address_pattern=r"^0x[a-fA-F0-9]{40}$",
            decimals=18,
            aliases=["test"],
            chain_type="evm",
        )
        assert isinstance(config, NetworkConfig)
        assert config.name == "testnet"
        assert config.symbol == "TST"
        assert config.rpc_url == "https://test.example.com"
        assert config.ws_url == "wss://test.example.com"
        assert config.decimals == 18
        assert config.aliases == ["test"]
        assert config.chain_type == "evm"

    def test_defaults(self) -> None:
        config = create_network_config(
            name="minimal",
            symbol="MIN",
            rpc_url="https://min.example.com",
        )
        assert config.decimals == 18
        assert config.chain_type == "evm"
        assert config.aliases == []
        assert config.ws_url is None
        assert config.address_pattern is None


class TestThreadSafety:
    def test_concurrent_registration(self) -> None:
        def register(idx: int) -> None:
            config = NetworkConfig(
                name=f"network_{idx}",
                symbol=f"N{idx}",
                rpc_url=f"https://rpc{idx}.example.com",
            )
            register_network(config)

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(register, range(50)))

        with _networks_lock:
            assert len(_registered_networks) == 50

        for i in range(50):
            assert get_network(f"network_{i}") is not None

    def test_concurrent_register_and_read(self) -> None:
        def register(idx: int) -> None:
            config = NetworkConfig(
                name=f"net_{idx}",
                symbol=f"N{idx}",
                rpc_url=f"https://r{idx}.example.com",
            )
            register_network(config)

        def read(name: str) -> NetworkConfig | None:
            return get_network(name)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(20):
                futures.append(executor.submit(register, i))
            for f in futures:
                f.result()

            read_results = list(executor.map(read, [f"net_{i}" for i in range(20)]))

        assert all(r is not None for r in read_results)


class TestValidateAddress:
    def test_valid_address_matches_pattern(self) -> None:
        config = NetworkConfig(
            name="eth",
            symbol="ETH",
            rpc_url="https://rpc.example.com",
            address_pattern=r"^0x[a-fA-F0-9]{40}$",
        )
        assert (
            config.validate_address("0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23")
            is True
        )

    def test_invalid_address_does_not_match(self) -> None:
        config = NetworkConfig(
            name="eth",
            symbol="ETH",
            rpc_url="https://rpc.example.com",
            address_pattern=r"^0x[a-fA-F0-9]{40}$",
        )
        assert config.validate_address("not_an_address") is False

    def test_returns_true_when_no_pattern(self) -> None:
        config = NetworkConfig(
            name="any",
            symbol="ANY",
            rpc_url="https://rpc.example.com",
        )
        assert config.validate_address("anything_at_all") is True
        assert config.validate_address("") is True
