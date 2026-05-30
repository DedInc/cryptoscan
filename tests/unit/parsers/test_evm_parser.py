from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from cryptoscan.core.config import UserConfig
from cryptoscan.core.models import PaymentStatus
from cryptoscan.networks import NetworkConfig
from cryptoscan.parsers.evm import EVMParser


@pytest.fixture
def parser(ethereum_config: NetworkConfig) -> EVMParser:
    client = MagicMock()
    client.config = UserConfig()
    return EVMParser(client, ethereum_config, "ETH")


def test_basic_parsing(
    parser: EVMParser, sample_evm_transaction: dict, sample_evm_block: dict
) -> None:
    result = parser.parse_transaction(
        sample_evm_transaction, block=sample_evm_block, latest_block_num=12345678
    )
    assert result.amount == Decimal("1")


def test_confirmations(
    parser: EVMParser, sample_evm_transaction: dict, sample_evm_block: dict
) -> None:
    result = parser.parse_transaction(
        sample_evm_transaction, block=sample_evm_block, latest_block_num=12345688
    )
    assert result.confirmations == 11


def test_no_block_pending(parser: EVMParser, sample_evm_transaction: dict) -> None:
    tx = {**sample_evm_transaction, "blockNumber": None}
    result = parser.parse_transaction(tx)
    assert result.status == PaymentStatus.PENDING


def test_receipt_failed(
    parser: EVMParser, sample_evm_transaction: dict, sample_evm_block: dict
) -> None:
    receipt = {"status": "0x0"}
    result = parser.parse_transaction(
        sample_evm_transaction, block=sample_evm_block, receipt=receipt
    )
    assert result.status == PaymentStatus.FAILED


def test_receipt_confirmed(
    parser: EVMParser, sample_evm_transaction: dict, sample_evm_block: dict
) -> None:
    receipt = {"status": "0x1"}
    result = parser.parse_transaction(
        sample_evm_transaction, block=sample_evm_block, receipt=receipt
    )
    assert result.status == PaymentStatus.CONFIRMED


def test_addresses(
    parser: EVMParser, sample_evm_transaction: dict, sample_evm_block: dict
) -> None:
    result = parser.parse_transaction(sample_evm_transaction, block=sample_evm_block)
    assert result.from_address == "0x1234567890123456789012345678901234567890"
    assert result.to_address == "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23"


def test_timestamp_from_block(
    parser: EVMParser, sample_evm_transaction: dict, sample_evm_block: dict
) -> None:
    result = parser.parse_transaction(sample_evm_transaction, block=sample_evm_block)
    expected = datetime.fromtimestamp(0x5F5E100, tz=timezone.utc)
    assert result.timestamp == expected
    assert result.timestamp.tzinfo == timezone.utc


def test_latest_block_num_none(
    parser: EVMParser, sample_evm_transaction: dict, sample_evm_block: dict
) -> None:
    result = parser.parse_transaction(
        sample_evm_transaction, block=sample_evm_block, latest_block_num=None
    )
    assert result.confirmations == 1
