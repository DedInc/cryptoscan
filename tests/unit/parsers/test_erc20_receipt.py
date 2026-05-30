from __future__ import annotations

from decimal import Decimal

from cryptoscan.core.models import PaymentStatus, TokenConfig
from cryptoscan.networks import NetworkConfig
from cryptoscan.parsers.evm import EVMParser

from .test_erc20_parser import (  # noqa: F401 — registers `config` fixture
    FROM_ADDR,
    TOKEN_CONTRACT,
    WALLET,
    WALLET_PADDED,
    _make_block,
    _make_receipt,
    _make_token_tx,
    _make_transfer_log,
    _mock_client,
    config,  # noqa: F401, F811
)


async def test_token_transfer_detected(config: NetworkConfig) -> None:  # noqa: F811
    block = _make_block([_make_token_tx()])
    receipt = _make_receipt(logs=[_make_transfer_log(amount_raw=1_000_000)])
    client = _mock_client(block, receipt=receipt)
    parser = EVMParser(client, config, "USDT")

    results = await parser.get_transactions(WALLET, 1, token_contract=TOKEN_CONTRACT)
    token_payments = [p for p in results if p.token_contract == TOKEN_CONTRACT]
    assert len(token_payments) == 1
    assert token_payments[0].amount == Decimal(1)
    assert token_payments[0].currency == "USDT"
    assert token_payments[0].from_address.lower() == FROM_ADDR.lower()
    assert token_payments[0].to_address.lower() == WALLET.lower()


async def test_token_transfer_wrong_recipient_ignored(config: NetworkConfig) -> None:  # noqa: F811
    other_wallet = "0xaaaa5555aaaa5555aaaa5555aaaa5555aaaa5555"
    block = _make_block([_make_token_tx()])
    receipt = _make_receipt(
        logs=[_make_transfer_log(to_addr=other_wallet, amount_raw=1_000_000)]
    )
    client = _mock_client(block, receipt=receipt)
    parser = EVMParser(client, config, "USDT")

    results = await parser.get_transactions(WALLET, 1, token_contract=TOKEN_CONTRACT)
    token_payments = [p for p in results if p.token_contract == TOKEN_CONTRACT]
    assert len(token_payments) == 0


async def test_token_transfer_wrong_contract_ignored(config: NetworkConfig) -> None:  # noqa: F811
    wrong_contract = "0xbbbb6666bbbb6666bbbb6666bbbb6666bbbb6666"
    block = _make_block([_make_token_tx(to_contract=wrong_contract)])
    receipt = _make_receipt(
        logs=[_make_transfer_log(address=wrong_contract, amount_raw=1_000_000)]
    )
    client = _mock_client(block, receipt=receipt)
    parser = EVMParser(client, config, "USDT")

    results = await parser.get_transactions(WALLET, 1, token_contract=TOKEN_CONTRACT)
    token_payments = [p for p in results if p.token_contract == TOKEN_CONTRACT]
    assert len(token_payments) == 0


async def test_token_transfer_failed_receipt(config: NetworkConfig) -> None:  # noqa: F811
    block = _make_block([_make_token_tx()])
    receipt = _make_receipt(
        logs=[_make_transfer_log(amount_raw=1_000_000)], status="0x0"
    )
    client = _mock_client(block, receipt=receipt)
    parser = EVMParser(client, config, "USDT")

    results = await parser.get_transactions(WALLET, 1, token_contract=TOKEN_CONTRACT)
    token_payments = [p for p in results if p.token_contract == TOKEN_CONTRACT]
    assert len(token_payments) == 1
    assert token_payments[0].status == PaymentStatus.FAILED


async def test_token_transfer_no_token_contract_skips_log_check(
    config: NetworkConfig,  # noqa: F811
) -> None:
    block = _make_block([_make_token_tx()])
    receipt = _make_receipt(logs=[_make_transfer_log(amount_raw=1_000_000)])
    client = _mock_client(block, receipt=receipt)
    parser = EVMParser(client, config, "USDT")

    results = await parser.get_transactions(WALLET, 1)
    token_payments = [p for p in results if p.token_contract]
    assert len(token_payments) == 0


async def test_token_transfer_with_token_config_usdt6(
    ethereum_config: NetworkConfig,
) -> None:
    tc = TokenConfig(contract_address=TOKEN_CONTRACT, symbol="USDT", decimals=6)
    block = _make_block([_make_token_tx()])
    receipt = _make_receipt(logs=[_make_transfer_log(amount_raw=10_000_000)])
    client = _mock_client(block, receipt=receipt)
    parser = EVMParser(client, ethereum_config, "ETH")

    results = await parser.get_transactions(WALLET, 1, token_contract=tc)
    token_payments = [p for p in results if p.token_contract == TOKEN_CONTRACT]
    assert len(token_payments) == 1
    assert token_payments[0].amount == Decimal(10)
    assert token_payments[0].currency == "USDT"


async def test_token_transfer_with_token_config_weth18(
    ethereum_config: NetworkConfig,
) -> None:
    tc = TokenConfig(contract_address=TOKEN_CONTRACT, symbol="WETH", decimals=18)
    raw = 2 * 10**18
    block = _make_block([_make_token_tx()])
    receipt = _make_receipt(logs=[_make_transfer_log(amount_raw=raw)])
    client = _mock_client(block, receipt=receipt)
    parser = EVMParser(client, ethereum_config, "ETH")

    results = await parser.get_transactions(WALLET, 1, token_contract=tc)
    token_payments = [p for p in results if p.token_contract == TOKEN_CONTRACT]
    assert len(token_payments) == 1
    assert token_payments[0].amount == Decimal(2)
    assert token_payments[0].currency == "WETH"


async def test_token_transfer_string_uses_network_decimals(
    config: NetworkConfig,  # noqa: F811
) -> None:
    block = _make_block([_make_token_tx()])
    receipt = _make_receipt(logs=[_make_transfer_log(amount_raw=50_000_000)])
    client = _mock_client(block, receipt=receipt)
    parser = EVMParser(client, config, "USDT")

    results = await parser.get_transactions(WALLET, 1, token_contract=TOKEN_CONTRACT)
    token_payments = [p for p in results if p.token_contract == TOKEN_CONTRACT]
    assert len(token_payments) == 1
    assert token_payments[0].amount == Decimal(50)
    assert token_payments[0].currency == "USDT"


def test_is_transfer_to_wallet() -> None:
    log = _make_transfer_log(amount_raw=500)
    assert EVMParser._is_transfer_to_wallet(log, TOKEN_CONTRACT, WALLET_PADDED) is True


def test_is_transfer_to_wallet_wrong_topic() -> None:
    log = _make_transfer_log(amount_raw=500)
    log["topics"][0] = "0x0000"
    assert EVMParser._is_transfer_to_wallet(log, TOKEN_CONTRACT, WALLET_PADDED) is False


def test_is_transfer_to_wallet_wrong_contract() -> None:
    log = _make_transfer_log(amount_raw=500)
    log["address"] = "0xaaaa0000aaaa0000aaaa0000aaaa0000aaaa0000"
    assert EVMParser._is_transfer_to_wallet(log, TOKEN_CONTRACT, WALLET_PADDED) is False


def test_is_transfer_to_wallet_wrong_recipient() -> None:
    log = _make_transfer_log(amount_raw=500)
    wrong_padded = "0x" + "0" * 24 + "bbbb" + "0" * 36
    assert EVMParser._is_transfer_to_wallet(log, TOKEN_CONTRACT, wrong_padded) is False


def test_parse_log_amount() -> None:
    assert EVMParser._parse_log_amount(hex(1_000_000)) == Decimal(1_000_000)
    assert EVMParser._parse_log_amount("0x0") == Decimal(0)
    assert EVMParser._parse_log_amount(hex(10**18)) == Decimal(10**18)
