from decimal import Decimal

import pytest

from cryptoscan.provider.universal_provider import amounts_match


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (Decimal("1.5"), Decimal("1.5"), True),
        (Decimal("1.500"), Decimal("1.5"), True),
        (Decimal("1.5"), Decimal("2.0"), False),
        (Decimal("0"), Decimal("0"), True),
        (Decimal("0.00000001"), Decimal("0.00000001"), True),
        (Decimal("999999999.999999999"), Decimal("999999999.999999999"), True),
        (Decimal("-0"), Decimal("0"), True),
        (Decimal("1E+2"), Decimal("100"), True),
        (Decimal("1.00"), Decimal("1.0"), True),
    ],
)
def test_amounts_match(a: Decimal, b: Decimal, expected: bool) -> None:
    assert amounts_match(a, b) is expected
