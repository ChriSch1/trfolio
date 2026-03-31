"""
components/__init__.py - Component Exports

Exportiert alle Dashboard Components für einfache Imports.
"""

from .overview import render_overview
from .stocks_deep_dive import render_stocks_deep_dive
from .crypto_deep_dive import render_crypto_deep_dive
from .etf_deep_dive import render_etf_deep_dive
from .income_deep_dive import render_income_deep_dive
from .transaction_log import render_transaction_log

__all__ = [
    'render_overview',
    'render_stocks_deep_dive',
    'render_crypto_deep_dive',
    'render_etf_deep_dive',
    'render_income_deep_dive',
    'render_transaction_log',
]
