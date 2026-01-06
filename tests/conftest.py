"""
Pytest configuration and fixtures for CryptoScan tests.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from cryptoscan.config import UserConfig
from cryptoscan.models import PaymentInfo, PaymentStatus
from cryptoscan.networks import NetworkConfig


# =============================================================================
# Event Loop Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Network Configuration Fixtures
# =============================================================================


@pytest.fixture
def ethereum_config() -> NetworkConfig:
    """Create Ethereum network configuration for testing."""
    return NetworkConfig(
        name="ethereum",
        symbol="ETH",
        rpc_url="https://ethereum-rpc.publicnode.com",
        ws_url="wss://ethereum-rpc.publicnode.com",
        address_pattern=r"^0x[a-fA-F0-9]{40}$",
        decimals=18,
        aliases=["eth"],
        chain_type="evm",
    )


@pytest.fixture
def solana_config() -> NetworkConfig:
    """Create Solana network configuration for testing."""
    return NetworkConfig(
        name="solana",
        symbol="SOL",
        rpc_url="https://solana-rpc.publicnode.com",
        ws_url="wss://solana-rpc.publicnode.com",
        address_pattern=r"^[1-9A-HJ-NP-Za-km-z]{32,44}$",
        decimals=9,
        aliases=["sol"],
        chain_type="solana",
    )


@pytest.fixture
def bitcoin_config() -> NetworkConfig:
    """Create Bitcoin network configuration for testing."""
    return NetworkConfig(
        name="bitcoin",
        symbol="BTC",
        rpc_url="https://bitcoin-rpc.publicnode.com",
        address_pattern=r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$",
        decimals=8,
        aliases=["btc"],
        chain_type="bitcoin",
    )


@pytest.fixture
def user_config() -> UserConfig:
    """Create user configuration for testing."""
    return UserConfig(
        timeout=10.0,
        max_retries=2,
        retry_delay=0.5,
        ssl_verify=True,
        max_blocks_to_scan=50,
        blocks_per_tx_multiplier=3,
    )


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_eth_address() -> str:
    """Sample Ethereum address for testing."""
    return "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23"


@pytest.fixture
def sample_sol_address() -> str:
    """Sample Solana address for testing."""
    return "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"


@pytest.fixture
def sample_btc_address() -> str:
    """Sample Bitcoin address for testing."""
    return "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"


@pytest.fixture
def sample_payment_info() -> PaymentInfo:
    """Create sample PaymentInfo for testing."""
    return PaymentInfo(
        transaction_id="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
        amount=Decimal("1.5"),
        currency="ETH",
        status=PaymentStatus.CONFIRMED,
        timestamp=datetime.now(timezone.utc),
        block_height=12345678,
        confirmations=10,
        fee=Decimal("0.001"),
        from_address="0x1234567890123456789012345678901234567890",
        to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
        raw_data={"test": "data"},
    )


@pytest.fixture
def sample_evm_block() -> dict:
    """Sample EVM block data for testing."""
    return {
        "number": "0xbc614e",  # 12345678
        "timestamp": "0x5f5e100",  # 100000000
        "transactions": [
            {
                "hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "from": "0x1234567890123456789012345678901234567890",
                "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
                "value": "0xde0b6b3a7640000",  # 1 ETH in wei
                "blockNumber": "0xbc614e",
            }
        ],
    }


@pytest.fixture
def sample_evm_transaction() -> dict:
    """Sample EVM transaction data for testing."""
    return {
        "hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "from": "0x1234567890123456789012345678901234567890",
        "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
        "value": "0xde0b6b3a7640000",  # 1 ETH in wei
        "blockNumber": "0xbc614e",
    }


@pytest.fixture
def sample_solana_transaction() -> dict:
    """Sample Solana transaction data for testing."""
    return {
        "transaction": {
            "signatures": [
                "5KtPn1LGuxhFiwjxErkxTb7XxtLVYUBe6Cn33ej7ATNQyXgzExvMGMKYz6D7xysgVW7bBTwLxCqzqzqzqzqzqzq"
            ],
            "message": {
                "accountKeys": [
                    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
                    "DRpbCBMxVnDK7maPM5tGv6MvB3v1sRMC86PZ8okm21hy",
                ],
            },
        },
        "meta": {
            "preBalances": [1000000000, 0],
            "postBalances": [500000000, 500000000],
            "fee": 5000,
            "err": None,
        },
        "slot": 123456789,
        "blockTime": 1609459200,
    }


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_rpc_client() -> MagicMock:
    """Create a mock RPC client."""
    client = MagicMock()
    client.connect = AsyncMock()
    client.close = AsyncMock()
    client.call = AsyncMock()
    return client


@pytest.fixture
def mock_http_response() -> MagicMock:
    """Create a mock HTTP response."""
    response = MagicMock()
    response.status_code = 200
    response.headers = {"content-type": "application/json", "content-length": "1000"}
    response.json = MagicMock(return_value={"result": {}})
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_websocket() -> AsyncMock:
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock(return_value='{"jsonrpc": "2.0", "result": {}}')
    ws.close = AsyncMock()
    return ws


# =============================================================================
# Async Test Helpers
# =============================================================================


@pytest.fixture
def async_mock() -> AsyncMock:
    """Create a basic AsyncMock for async function mocking."""
    return AsyncMock()


# =============================================================================
# Cleanup Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def cleanup_registered_networks():
    """Clean up registered networks after each test."""
    from cryptoscan.networks import _registered_networks, _networks_lock

    yield

    with _networks_lock:
        _registered_networks.clear()
