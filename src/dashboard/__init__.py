"""
Dashboard module initialization.
Exposes key functions for easier import.
"""

# Config Loaders
from .config_loader import (
    get_db_connection,
    load_transactions,
    calculate_holdings,
    calculate_etf_holdings,
    calculate_interest_income,
    load_trades,
)

# Data Loaders
from .data_loader import (
    load_current_prices_auto_currency,
    fetch_sectors,
    build_ticker_mapping,
)

# Calculations
from .calculations import (
    calculate_stock_returns,
    calculate_etf_returns,
    calculate_crypto_returns,
    extract_sold_positions,
)

# Components
from .components import (
    render_overview,
    render_stocks_deep_dive,
    render_crypto_deep_dive,
    render_etf_deep_dive,
    render_income_deep_dive,
    render_transaction_log,
)
