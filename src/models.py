from enum import Enum
from typing import Optional
from datetime import datetime
from typing_extensions import Self
from pydantic import BaseModel, model_validator, field_validator


class EventType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    ETF_SAVING_PLAN = "etf_saving_plan"
    INTEREST = "interest"


class Record(BaseModel):
    name: Optional[str] = None
    clean_name: Optional[str] = None
    date: str
    event_type: EventType
    isin: Optional[str] = None
    ticker: Optional[str] = None
    unit_amount: Optional[float] = None
    unit_price: Optional[float] = None
    dividend_per_share: Optional[float] = None
    currency: str
    exchange_rate: Optional[float] = None
    gross_amount: float
    net_cashflow: float
    external_fee: Optional[float] = 0.0
    foreign_tax: Optional[float] = 0.0
    capital_tax: Optional[float] = 0.0
    church_tax: Optional[float] = 0.0
    soli_tax: Optional[float] = 0.0
    financial_transaction_tax: Optional[float] = 0.0
    is_crypto: Optional[bool] = False

    @model_validator(mode='after')
    def validate_net_cash_flow(self) -> Self:
        computed = self.gross_amount

        if self.event_type.lower() == 'buy':
            computed += (self.external_fee or 0.0)
            computed += (self.financial_transaction_tax or 0.0)
        if self.event_type.lower() == "dividend":
            computed -= (self.foreign_tax or 0.0)
            computed -= (self.capital_tax or 0.0)
            computed -= (self.church_tax or 0.0)
            computed -= (self.soli_tax or 0.0)
        if self.event_type.lower() == "sell":
            computed -= (self.external_fee or 0.0)
            computed -= (self.foreign_tax or 0.0)
            computed -= (self.capital_tax or 0.0)
            computed -= (self.church_tax or 0.0)
            computed -= (self.soli_tax or 0.0)
            computed -= (self.financial_transaction_tax or 0.0)
        if self.event_type.lower() == "interest":
            computed = self.net_cashflow

        tolerance = 0.01
        if abs(self.net_cashflow - computed) > tolerance:
            raise ValueError(
                f"net_cashflow mismatch for {self.event_type}: "
                f"extracted = {self.net_cashflow:.2f}, computed= {computed:.2f} "
                f"(gross={self.gross_amount:.2f}, external_fee={self.external_fee or 0:.2f}, "
                f"foreign_tax={self.foreign_tax or 0:.2f}, capital_tax={self.capital_tax or 0:.2f}, "
                f"church_tax={self.church_tax or 0:.2f}, soli_tax={self.soli_tax or 0:.2f})"
            )
        return self

    @field_validator("date", mode="before")
    @classmethod
    def normalize_date(cls, v):
        """Convert various date formats to ISO YYYY-MM-DD."""
        if isinstance(v, str):
            clean = v.replace("-", "").replace("/", "").replace(".", "").strip()

            if len(clean) == 8 and clean.isdigit():
                dt = datetime.strptime(clean, "%Y%m%d")
                return dt.strftime("%Y-%m-%d")

            if len(v) == 10 and v[4] == "-" and v[7] == "-":
                return v

            for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y"]:
                try:
                    dt = datetime.strptime(v, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

            raise ValueError(f"Cannot parse date: {v}")

        return v
