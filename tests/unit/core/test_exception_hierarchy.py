import pytest

from cryptoscan.core.exceptions import (
    AdapterError,
    BlockFetchError,
    ConnectionError,
    CryptoScanError,
    CSConnectionError,
    CSTimeoutError,
    NetworkError,
    ParserError,
    PaymentNotFoundError,
    RPCError,
    TimeoutError,
    ValidationError,
)


class TestExceptionSubclassing:
    def test_network_error_is_cryptoscan_error(self) -> None:
        assert issubclass(NetworkError, CryptoScanError)

    def test_cs_connection_error_is_cryptoscan_error(self) -> None:
        assert issubclass(CSConnectionError, CryptoScanError)

    def test_cs_timeout_error_is_cryptoscan_error(self) -> None:
        assert issubclass(CSTimeoutError, CryptoScanError)

    def test_payment_not_found_error_is_cryptoscan_error(self) -> None:
        assert issubclass(PaymentNotFoundError, CryptoScanError)

    def test_validation_error_is_cryptoscan_error(self) -> None:
        assert issubclass(ValidationError, CryptoScanError)

    def test_rpc_error_is_cryptoscan_error(self) -> None:
        assert issubclass(RPCError, CryptoScanError)

    def test_parser_error_is_cryptoscan_error(self) -> None:
        assert issubclass(ParserError, CryptoScanError)

    def test_block_fetch_error_is_cryptoscan_error(self) -> None:
        assert issubclass(BlockFetchError, CryptoScanError)

    def test_adapter_error_is_cryptoscan_error(self) -> None:
        assert issubclass(AdapterError, CryptoScanError)


class TestNetworkErrorHierarchy:
    def test_cs_connection_error_is_network_error(self) -> None:
        assert issubclass(CSConnectionError, NetworkError)

    def test_cs_timeout_error_is_network_error(self) -> None:
        assert issubclass(CSTimeoutError, NetworkError)

    def test_block_fetch_error_is_network_error(self) -> None:
        assert issubclass(BlockFetchError, NetworkError)


class TestExceptionAttributes:
    def test_network_error_stores_message_and_original(self) -> None:
        original = ValueError("inner")
        exc = NetworkError("connection failed", original)
        assert exc.message == "connection failed"
        assert exc.original_error is original

    def test_network_error_original_defaults_to_none(self) -> None:
        exc = NetworkError("fail")
        assert exc.original_error is None

    def test_rpc_error_stores_message_code_data(self) -> None:
        exc = RPCError("not found", code=-32601, data={"detail": "x"})
        assert exc.message == "not found"
        assert exc.code == -32601
        assert exc.data == {"detail": "x"}

    def test_rpc_error_code_defaults_to_none(self) -> None:
        exc = RPCError("err")
        assert exc.code is None

    def test_rpc_error_data_defaults_to_empty_dict(self) -> None:
        exc = RPCError("err")
        assert exc.data == {}

    def test_parser_error_stores_message_txid_original(self) -> None:
        original = TypeError("bad")
        exc = ParserError("parse fail", transaction_id="0xabc", original_error=original)
        assert exc.message == "parse fail"
        assert exc.transaction_id == "0xabc"
        assert exc.original_error is original

    def test_parser_error_defaults(self) -> None:
        exc = ParserError("fail")
        assert exc.transaction_id is None
        assert exc.original_error is None

    def test_block_fetch_error_stores_block_number(self) -> None:
        original = OSError("io")
        exc = BlockFetchError("block fail", block_number=12345, original_error=original)
        assert exc.message == "block fail"
        assert exc.block_number == 12345
        assert exc.original_error is original

    def test_block_fetch_error_block_number_defaults_to_none(self) -> None:
        exc = BlockFetchError("fail")
        assert exc.block_number is None

    def test_adapter_error_stores_adapter_name_and_original(self) -> None:
        original = RuntimeError("adapter boom")
        exc = AdapterError(
            "adapter fail", adapter_name="ton_center", original_error=original
        )
        assert exc.message == "adapter fail"
        assert exc.adapter_name == "ton_center"
        assert exc.original_error is original

    def test_adapter_error_defaults(self) -> None:
        exc = AdapterError("fail")
        assert exc.adapter_name is None
        assert exc.original_error is None


class TestBackwardCompatAliases:
    def test_connection_error_alias_is_cs_connection_error(self) -> None:
        assert ConnectionError is CSConnectionError

    def test_timeout_error_alias_is_cs_timeout_error(self) -> None:
        assert TimeoutError is CSTimeoutError


class TestCatchAsCryptoScanError:
    def test_catch_network_error(self) -> None:
        with pytest.raises(CryptoScanError):
            raise NetworkError("fail")

    def test_catch_cs_connection_error(self) -> None:
        with pytest.raises(CryptoScanError):
            raise CSConnectionError("fail")

    def test_catch_cs_timeout_error(self) -> None:
        with pytest.raises(CryptoScanError):
            raise CSTimeoutError("fail")

    def test_catch_payment_not_found_error(self) -> None:
        with pytest.raises(CryptoScanError):
            raise PaymentNotFoundError("not found")

    def test_catch_validation_error(self) -> None:
        with pytest.raises(CryptoScanError):
            raise ValidationError("invalid")

    def test_catch_rpc_error(self) -> None:
        with pytest.raises(CryptoScanError):
            raise RPCError("rpc fail")

    def test_catch_parser_error(self) -> None:
        with pytest.raises(CryptoScanError):
            raise ParserError("parse fail")

    def test_catch_block_fetch_error(self) -> None:
        with pytest.raises(CryptoScanError):
            raise BlockFetchError("block fail")

    def test_catch_adapter_error(self) -> None:
        with pytest.raises(CryptoScanError):
            raise AdapterError("adapter fail")
