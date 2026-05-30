from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from cryptoscan.core.config import UserConfig
from cryptoscan.core.exceptions import NetworkError
from cryptoscan.core.models import PaymentInfo, PaymentStatus
from cryptoscan.monitoring.strategies import PollingStrategy


def _make_payment(
    tx_id: str = "0xabc123",
    amount: Decimal = Decimal("1.0"),
    confirmations: int = 5,
    timestamp: datetime | None = None,
) -> PaymentInfo:
    return PaymentInfo(
        transaction_id=tx_id,
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
        amount=amount,
        currency="ETH",
        status=PaymentStatus.CONFIRMED,
        timestamp=timestamp or datetime.now(timezone.utc),
        block_height=100,
        confirmations=confirmations,
        from_address="0x1111111111111111111111111111111111111111",
        to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
    )


def _future_payment(**kwargs: object) -> PaymentInfo:
    from datetime import timedelta

    kwargs.setdefault("timestamp", datetime.now(timezone.utc) + timedelta(hours=1))
    return _make_payment(**kwargs)


def _make_strategy(
    auto_stop: bool = True, min_confirmations: int = 1, poll_interval: float = 0.01
) -> PollingStrategy:
    provider = MagicMock()
    provider.find_payment = AsyncMock(return_value=None)
    config = UserConfig(retry_delay=0.01)
    return PollingStrategy(
        provider=provider,
        wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f8fE23",
        expected_amount=Decimal("1.0"),
        config=config,
        poll_interval=poll_interval,
        max_transactions=10,
        auto_stop=auto_stop,
        min_confirmations=min_confirmations,
    )


async def test_payment_found_auto_stop() -> None:
    strategy = _make_strategy(auto_stop=True)
    payment = _future_payment()
    strategy.provider.find_payment = AsyncMock(return_value=payment)

    received = []

    async def on_payment(p: PaymentInfo) -> None:
        received.append(p)
        strategy._stop_event.set()

    await strategy.monitor(on_payment, AsyncMock())
    assert len(received) == 1
    assert received[0].transaction_id == "0xabc123"


async def test_no_payment_loop_continues() -> None:
    strategy = _make_strategy(auto_stop=False, poll_interval=0.01)
    calls = 0

    async def find_payment_side_effect(
        *_args: object, **_kwargs: object
    ) -> PaymentInfo | None:
        nonlocal calls
        calls += 1
        if calls >= 4:
            strategy._stop_event.set()
        return None

    strategy.provider.find_payment = AsyncMock(side_effect=find_payment_side_effect)

    await strategy.monitor(AsyncMock(), AsyncMock())
    assert calls >= 4


async def test_already_seen_skipped() -> None:
    strategy = _make_strategy(auto_stop=False, poll_interval=0.01)
    payment = _future_payment(tx_id="0xdeadbeef")
    call_count = 0

    async def find_payment_side_effect(
        *_args: object, **_kwargs: object
    ) -> PaymentInfo | None:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return payment
        if call_count >= 4:
            strategy._stop_event.set()
        return None

    strategy.provider.find_payment = AsyncMock(side_effect=find_payment_side_effect)

    received = []

    async def on_payment(p: PaymentInfo) -> None:
        received.append(p)

    await strategy.monitor(on_payment, AsyncMock())
    assert len(received) == 1


async def test_prestart_transaction_skipped() -> None:
    strategy = _make_strategy(auto_stop=False, poll_interval=0.01)
    old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    old_payment = _make_payment(tx_id="0xold", timestamp=old_time)
    call_count = 0

    async def find_payment_side_effect(
        *_args: object, **_kwargs: object
    ) -> PaymentInfo | None:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return old_payment
        if call_count >= 4:
            strategy._stop_event.set()
        return None

    strategy.provider.find_payment = AsyncMock(side_effect=find_payment_side_effect)

    received = []

    async def on_payment(p: PaymentInfo) -> None:
        received.append(p)

    await strategy.monitor(on_payment, AsyncMock())
    assert len(received) == 0


async def test_insufficient_confirmations_skipped() -> None:
    strategy = _make_strategy(auto_stop=False, poll_interval=0.01, min_confirmations=10)
    payment = _future_payment(confirmations=2)
    call_count = 0

    async def find_payment_side_effect(
        *_args: object, **_kwargs: object
    ) -> PaymentInfo | None:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return payment
        if call_count >= 4:
            strategy._stop_event.set()
        return None

    strategy.provider.find_payment = AsyncMock(side_effect=find_payment_side_effect)

    received = []

    async def on_payment(p: PaymentInfo) -> None:
        received.append(p)

    await strategy.monitor(on_payment, AsyncMock())
    assert len(received) == 0


async def test_network_error_continues() -> None:
    strategy = _make_strategy(auto_stop=False, poll_interval=0.01)
    call_count = 0

    async def find_payment_side_effect(
        *_args: object, **_kwargs: object
    ) -> PaymentInfo | None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise NetworkError("connection lost")
        if call_count == 2:
            return _future_payment(tx_id="0xtx2")
        if call_count >= 4:
            strategy._stop_event.set()
        return None

    strategy.provider.find_payment = AsyncMock(side_effect=find_payment_side_effect)

    received = []
    errors = []

    async def on_payment(p: PaymentInfo) -> None:
        received.append(p)

    async def on_error(e: Exception) -> None:
        errors.append(e)

    await strategy.monitor(on_payment, on_error)
    assert len(errors) == 1
    assert isinstance(errors[0], NetworkError)
    assert len(received) >= 1
