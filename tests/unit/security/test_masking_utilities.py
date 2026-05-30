from cryptoscan.security import (
    mask_address,
    mask_transaction_id,
    mask_url,
    sanitize_log_data,
)


class TestMaskUrl:
    def test_masks_path_beyond_second_segment(self) -> None:
        result = mask_url("wss://host.com/v2/secret")
        assert result == "wss://host.com/v2/***MASKED***"

    def test_masks_deep_path(self) -> None:
        result = mask_url("https://host.com/v2/api/keys/tokens")
        assert result == "https://host.com/v2/***MASKED***"

    def test_hides_query_params(self) -> None:
        result = mask_url("https://host.com/path?key=val")
        assert result == "https://host.com/path?***MASKED***"

    def test_short_path_untouched(self) -> None:
        result = mask_url("https://rpc.example.com")
        assert result == "https://rpc.example.com"

    def test_root_path_untouched(self) -> None:
        result = mask_url("https://rpc.example.com/")
        assert result == "https://rpc.example.com/"

    def test_empty_returns_empty_string(self) -> None:
        assert mask_url("") == ""

    def test_none_returns_empty_string(self) -> None:
        assert mask_url(None) == ""

    def test_invalid_url_returns_invalid_marker(self) -> None:
        result = mask_url("not-a-valid-url")
        assert result == "***INVALID_URL***"

    def test_preserves_scheme(self) -> None:
        result = mask_url("wss://host.com/v1/key123")
        assert result.startswith("wss://")

    def test_single_path_segment_preserved(self) -> None:
        result = mask_url("https://host.com/path")
        assert result == "https://host.com/path"


class TestMaskAddress:
    def test_normal_address_masked(self) -> None:
        addr = "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23"
        assert mask_address(addr) == "0x742d35...f8fE23"

    def test_short_string_returned_as_is(self) -> None:
        assert mask_address("short") == "short"

    def test_exactly_min_length_returned_as_is(self) -> None:
        assert mask_address("a" * 11) == "a" * 11

    def test_at_min_length_gets_masked(self) -> None:
        addr = "a" * 15
        result = mask_address(addr)
        assert "..." in result

    def test_none_returns_empty_string(self) -> None:
        assert mask_address(None) == ""

    def test_empty_returns_empty_string(self) -> None:
        assert mask_address("") == ""


class TestMaskTransactionId:
    def test_long_tx_id_masked(self) -> None:
        tx_id = "0xabcdef1234567890abcdef1234567890abcdef1234567890abcd"
        result = mask_transaction_id(tx_id)
        assert result == "0xabcdef12345678..."

    def test_shows_first_16_chars(self) -> None:
        tx_id = "a" * 32
        result = mask_transaction_id(tx_id)
        assert result == "aaaaaaaaaaaaaaaa..."

    def test_short_tx_id_returned_as_is(self) -> None:
        tx_id = "0x1234"
        assert mask_transaction_id(tx_id) == "0x1234"

    def test_exactly_16_chars_returned_as_is(self) -> None:
        tx_id = "a" * 16
        assert mask_transaction_id(tx_id) == tx_id

    def test_17_chars_gets_masked(self) -> None:
        tx_id = "a" * 17
        result = mask_transaction_id(tx_id)
        assert result == "aaaaaaaaaaaaaaaa..."

    def test_none_returns_empty_string(self) -> None:
        assert mask_transaction_id(None) == ""

    def test_empty_returns_empty_string(self) -> None:
        assert mask_transaction_id("") == ""


class TestSanitizeLogData:
    def test_address_keys_masked(self) -> None:
        data = {"address": "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23"}
        result = sanitize_log_data(data)
        assert result["address"] == "0x742d35...f8fE23"

    def test_hash_key_masked_with_transaction_mask(self) -> None:
        long_hash = "0xabcdef1234567890abcdef1234567890"
        data = {"hash": long_hash}
        result = sanitize_log_data(data)
        assert result["hash"] == "0xabcdef12345678..."

    def test_tx_id_masked_with_transaction_mask(self) -> None:
        long_tx = "abcdef1234567890abcdef1234567890"
        data = {"tx_id": long_tx}
        result = sanitize_log_data(data)
        assert result["tx_id"] == "abcdef1234567890..."

    def test_api_key_masked(self) -> None:
        data = {"api_key": "super-secret-api-key-12345"}
        result = sanitize_log_data(data)
        assert result["api_key"] == "***MASKED***"

    def test_secret_masked(self) -> None:
        data = {"secret": "my-secret-value"}
        result = sanitize_log_data(data)
        assert result["secret"] == "***MASKED***"

    def test_nested_dicts_handled_recursively(self) -> None:
        data = {
            "outer": {
                "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
                "amount": "1.5",
            }
        }
        result = sanitize_log_data(data)
        assert result["outer"]["address"] == "0x742d35...f8fE23"
        assert result["outer"]["amount"] == "1.5"

    def test_non_sensitive_keys_passed_through(self) -> None:
        data = {"amount": "1.5", "currency": "ETH", "status": "confirmed"}
        result = sanitize_log_data(data)
        assert result == data

    def test_wallet_address_masked(self) -> None:
        data = {"wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23"}
        result = sanitize_log_data(data)
        assert result["wallet_address"] == "0x742d35...f8fE23"

    def test_from_address_masked(self) -> None:
        data = {"from_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23"}
        result = sanitize_log_data(data)
        assert result["from_address"] == "0x742d35...f8fE23"

    def test_password_masked(self) -> None:
        data = {"password": "hunter2"}
        result = sanitize_log_data(data)
        assert result["password"] == "***MASKED***"

    def test_transaction_id_masked(self) -> None:
        data = {"transaction_id": "abcdef1234567890abcdef1234567890"}
        result = sanitize_log_data(data)
        assert "..." in result["transaction_id"]
