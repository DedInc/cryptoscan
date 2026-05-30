from decimal import Decimal

from cryptoscan.core.models import MatchMode, match_amount


class TestMatchAmountExact:
    def test_equal(self) -> None:
        assert match_amount(Decimal("1.5"), Decimal("1.5"), MatchMode.EXACT) is True

    def test_equal_normalized(self) -> None:
        assert match_amount(Decimal("1.500"), Decimal("1.5"), MatchMode.EXACT) is True

    def test_not_equal(self) -> None:
        assert match_amount(Decimal("1.5"), Decimal("2.0"), MatchMode.EXACT) is False

    def test_slightly_off(self) -> None:
        assert match_amount(Decimal("1.01"), Decimal("1.00"), MatchMode.EXACT) is False


class TestMatchAmountAtLeast:
    def test_greater(self) -> None:
        assert match_amount(Decimal("2.0"), Decimal("1.5"), MatchMode.AT_LEAST) is True

    def test_equal(self) -> None:
        assert match_amount(Decimal("1.5"), Decimal("1.5"), MatchMode.AT_LEAST) is True

    def test_less(self) -> None:
        assert match_amount(Decimal("1.0"), Decimal("1.5"), MatchMode.AT_LEAST) is False


class TestMatchAmountAny:
    def test_any_amount(self) -> None:
        assert match_amount(Decimal("0.01"), Decimal("100"), MatchMode.ANY) is True

    def test_any_zero(self) -> None:
        assert match_amount(Decimal("0"), Decimal("100"), MatchMode.ANY) is True

    def test_any_huge(self) -> None:
        assert match_amount(Decimal("999999"), Decimal("0.001"), MatchMode.ANY) is True

    def test_any_none_expected(self) -> None:
        assert match_amount(Decimal("5.0"), None, MatchMode.ANY) is True


class TestMatchAmountNoneExpected:
    def test_exact_none_returns_false(self) -> None:
        assert match_amount(Decimal("1.0"), None, MatchMode.EXACT) is False

    def test_at_least_none_returns_false(self) -> None:
        assert match_amount(Decimal("1.0"), None, MatchMode.AT_LEAST) is False

    def test_any_none_returns_true(self) -> None:
        assert match_amount(Decimal("1.0"), None, MatchMode.ANY) is True


class TestMatchModeEnum:
    def test_values(self) -> None:
        assert MatchMode.EXACT.value == "exact"
        assert MatchMode.AT_LEAST.value == "at_least"
        assert MatchMode.ANY.value == "any"

    def test_from_string(self) -> None:
        assert MatchMode("exact") == MatchMode.EXACT
        assert MatchMode("at_least") == MatchMode.AT_LEAST
        assert MatchMode("any") == MatchMode.ANY
