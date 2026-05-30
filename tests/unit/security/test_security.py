import pytest

from cryptoscan.security import (
    mask_address,
    mask_transaction_id,
    mask_url,
    validate_rpc_url,
    validate_ws_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data",
        "http://127.0.0.1:8545",
        "http://10.0.0.1:8545",
    ],
)
def test_validate_rpc_url_blocks_private_ips(url: str) -> None:
    assert validate_rpc_url(url) is False


def test_validate_rpc_url_allows_public_url() -> None:
    assert validate_rpc_url("https://mainnet.infura.io/v3/abc") is True


def test_validate_ws_url_allows_valid() -> None:
    assert validate_ws_url("wss://mainnet.infura.io/ws/v3/abc") is True


def test_validate_ws_url_rejects_http_scheme() -> None:
    assert validate_ws_url("http://127.0.0.1:8546") is False


def test_mask_url_hides_sensitive_path_and_query() -> None:
    masked = mask_url("https://api.example.com/v1/key123?api_key=secret")
    assert "key123" not in masked
    assert "secret" not in masked


def test_mask_address_returns_masked_version() -> None:
    addr = "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23"
    masked = mask_address(addr)
    assert masked.startswith("0x")
    assert "..." in masked
    assert len(masked) < len(addr)


def test_mask_transaction_id_returns_masked_version() -> None:
    tx_id = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    masked = mask_transaction_id(tx_id)
    assert masked.endswith("...")
    assert len(masked) < len(tx_id)
