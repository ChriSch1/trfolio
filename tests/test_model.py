import pytest

from src.models import Record
from pydantic import ValidationError

def test_buy_only_external_fee():
    """Buy: net = gross - external_fee (no taxes)"""
    rec = Record(
        name="Test", date="2025-10-25", event_type="buy", isin="US123",
        unit_price=100.0, unit_amount=10.0, currency="EUR",
        gross_amount=1000.0,
        external_fee=5.0,
        # Taxes present but should be ignored for buys
        foreign_tax=10.0, capital_tax=5.0,
        net_cash_flow=995.0  # 1000 - 5 = 995 (taxes not subtracted)
    )
    assert rec.net_cash_flow == 995.0

def test_sell_all_fees_and_taxes():
    """Sell: net = gross - external_fee - all taxes"""
    rec = Record(
        name="Test", date="2025-10-25", event_type="sell", isin="US123",
        unit_price=100.0, unit_amount=10.0, currency="EUR",
        gross_amount=1000.0,
        external_fee=5.0,
        foreign_tax=10.0,
        capital_tax=50.0,
        church_tax=5.0,
        soli_tax=2.5,
        net_cash_flow=927.5  # 1000 - 5 - 10 - 50 - 5 - 2.5
    )
    assert rec.net_cash_flow == 927.5

def test_dividend_all_fees_and_taxes():
    """Dividend: net = gross - external_fee - all taxes"""
    rec = Record(
        name="Test", date="2025-10-25", event_type="dividend", isin="US123",
        unit_price=100.0, unit_amount=10.0, currency="EUR",
        gross_amount=500.0,
        external_fee=0.0,
        foreign_tax=75.0,
        capital_tax=25.0,
        net_cash_flow=400.0  # 500 - 75 - 25
    )
    assert rec.net_cash_flow == 400.0

def test_buy_mismatch_raises():
    """Buy with incorrect net raises validation error"""
    with pytest.raises(ValidationError) as exc:
        Record(
            name="Test", date="2025-10-25", event_type="buy", isin="US123",
            unit_price=100.0, unit_amount=10.0, currency="EUR",
            gross_amount=1000.0,
            external_fee=5.0,
            net_cash_flow=900.0  # Wrong: should be 995
        )
    errs = exc.value.errors()
    assert any("net_cash_flow mismatch" in str(e.get("msg", "")) for e in errs)

def test_sell_mismatch_raises():
    """Sell with incorrect net raises validation error"""
    with pytest.raises(ValidationError) as exc:
        Record(
            name="Test", date="2025-10-25", event_type="sell", isin="US123",
            unit_price=100.0, unit_amount=10.0, currency="EUR",
            gross_amount=1000.0,
            external_fee=5.0,
            capital_tax=50.0,
            net_cash_flow=995.0  # Wrong: didn't subtract capital_tax
        )
    errs = exc.value.errors()
    assert any("net_cash_flow mismatch" in str(e.get("msg", "")) for e in errs)
