"""ERC-20 token receipt/log helpers for EVM chains."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from ..core.models import PaymentInfo, PaymentStatus, TokenConfig

ERC20_TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
)


def is_transfer_to_wallet(log: dict, token_contract: str, wallet_padded: str) -> bool:
    """Check whether a log entry is an ERC-20 Transfer to *wallet_padded*."""
    topics = log.get("topics", [])
    if len(topics) < 3:
        return False
    if topics[0] != ERC20_TRANSFER_TOPIC:
        return False
    log_addr = log.get("address", "")
    if log_addr.lower() != token_contract.lower():
        return False
    return topics[2].lower() == wallet_padded


def parse_log_amount(data: str) -> Decimal:
    """Parse the ``data`` field of an ERC-20 log entry into a raw Decimal."""
    return Decimal(int(data, 16))


def resolve_token_config_for_evm(
    token_contract: str | TokenConfig,
    network_config_decimals: int,
    currency_symbol: str,
) -> tuple[str, int, str]:
    """Resolve token contract into (address, decimals, symbol)."""
    if isinstance(token_contract, TokenConfig):
        return (
            token_contract.contract_address,
            token_contract.decimals,
            token_contract.symbol,
        )
    return (token_contract, network_config_decimals, currency_symbol)


def parse_token_payment_from_log(
    log: dict,
    tx: dict,
    block: dict,
    receipt: dict,
    wallet_address: str,
    token_address: str,
    decimals: int,
    symbol: str,
    latest_block_num: int,
) -> PaymentInfo:
    """Build a ``PaymentInfo`` from a matched ERC-20 transfer log."""
    raw_amount = parse_log_amount(log["data"])
    amount = raw_amount / Decimal(10**decimals)
    block_number = int(block.get("number", "0x0"), 16)
    timestamp = datetime.fromtimestamp(
        int(block.get("timestamp", "0x0"), 16), tz=timezone.utc
    )
    confirmations = max(latest_block_num - block_number + 1, 1)

    status = PaymentStatus.CONFIRMED
    if receipt.get("status") == "0x0":
        status = PaymentStatus.FAILED

    from_addr = "0x" + log["topics"][1][-40:] if len(log["topics"]) > 1 else ""

    return PaymentInfo(
        transaction_id=tx["hash"],
        wallet_address=wallet_address,
        amount=amount,
        currency=symbol,
        status=status,
        timestamp=timestamp,
        block_height=block_number,
        confirmations=confirmations,
        fee=None,
        from_address=from_addr,
        to_address=wallet_address,
        token_contract=token_address,
        raw_data={"tx": tx, "receipt": receipt, "block": block, "log": log},
    )
