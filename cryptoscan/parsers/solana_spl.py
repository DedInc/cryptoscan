"""SPL token balance/delta helpers for Solana."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from ..core.models import PaymentInfo, PaymentStatus


def build_balance_map(balances: list[dict]) -> dict[int, dict]:
    """Index token balance entries by their ``accountIndex``."""
    result: dict[int, dict] = {}
    for b in balances:
        idx = b.get("accountIndex")
        if idx is not None:
            result[idx] = b
    return result


def compute_incoming_delta(
    post_balances: list[dict],
    pre_map: dict[int, dict],
    token_addr: str,
    wallet_address: str,
) -> tuple[Decimal, int, Decimal] | None:
    """Find the first post-balance showing an incoming token delta.

    Returns ``(delta_raw_decimal, account_index, post_amount)`` or ``None``.
    """
    for post in post_balances:
        if post.get("mint") != token_addr:
            continue
        if post.get("owner") != wallet_address:
            continue

        post_amt_raw = (post.get("uiTokenAmount") or {}).get("amount", "0")
        idx = post.get("accountIndex")
        pre_entry = pre_map.get(idx) if idx is not None else None
        pre_amt_raw = (
            (pre_entry.get("uiTokenAmount") or {}).get("amount", "0")
            if pre_entry
            else "0"
        )

        post_amt = Decimal(str(post_amt_raw))
        pre_amt = Decimal(str(pre_amt_raw))
        delta_raw = post_amt - pre_amt

        if delta_raw <= 0:
            continue

        return (delta_raw, idx or 0, post_amt)

    return None


def find_spl_sender(
    pre_balances: list[dict],
    post_balances: list[dict],
    token_addr: str,
    wallet_address: str,
) -> str:
    """Identify the sender of an SPL transfer by scanning balance deltas."""
    post_map: dict[int, str] = {}
    for b in post_balances:
        idx = b.get("accountIndex")
        if idx is not None:
            post_map[idx] = (b.get("uiTokenAmount") or {}).get("amount", "0")

    for pre in pre_balances:
        if pre.get("mint") != token_addr:
            continue
        if pre.get("owner") == wallet_address:
            continue
        idx = pre.get("accountIndex")
        if idx is None:
            continue
        pre_amt = Decimal(str((pre.get("uiTokenAmount") or {}).get("amount", "0")))
        post_amt = Decimal(str(post_map.get(idx, "0")))
        if post_amt < pre_amt:
            return pre.get("owner", "")
    return ""


def build_spl_payment_info(
    result: dict,
    wallet_address: str,
    amount: Decimal,
    token_addr: str,
    decimals: int,  # noqa: ARG001
    symbol: str,
    from_address: str,
    network_decimals: int,
) -> PaymentInfo:
    """Construct a ``PaymentInfo`` for an SPL token transfer."""
    meta = result.get("meta") or {}
    status = (
        PaymentStatus.CONFIRMED if meta.get("err") is None else PaymentStatus.FAILED
    )

    return PaymentInfo(
        transaction_id=(
            result.get("transaction", {}).get("signatures", [""])[0]
            if result.get("transaction")
            else ""
        ),
        wallet_address=wallet_address,
        amount=amount,
        currency=symbol,
        status=status,
        timestamp=datetime.fromtimestamp(result.get("blockTime", 0), tz=timezone.utc),
        block_height=result.get("slot"),
        confirmations=0,
        fee=Decimal(meta.get("fee", 0)) / Decimal(10**network_decimals),
        from_address=from_address,
        to_address=wallet_address,
        token_contract=token_addr,
        raw_data=result,
    )
