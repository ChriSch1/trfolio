"""
TRfolio - Multi-Stream Portfolio Dashboard
Main Entry Point
"""
import os
import streamlit as st
import pandas as pd
from datetime import datetime

# --- Internal Modules ---
from src.config import settings

# 1. Data Loaders
from src.dashboard.config_loader import (
    get_db_connection,
    load_transactions,
    calculate_holdings,
    load_trades,
    calculate_etf_holdings,
    calculate_interest_income
)
from src.dashboard.data_loader import (
    load_current_prices_auto_currency,
    fetch_sectors
)

# 2. Logic & Calculations
from src.dashboard.calculations import (
    calculate_stock_returns,
    calculate_etf_returns,
    calculate_crypto_returns
)

# 3. UI Components
from src.dashboard.sidebar import render_sidebar
from src.dashboard.components import (
    render_overview,
    render_stocks_deep_dive,
    render_crypto_deep_dive,
    render_etf_deep_dive,
    render_income_deep_dive,
    render_transaction_log
)

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="TRFolio",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================
def load_custom_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif;
            }

            h1, h2, h3 {
                font-family: 'Inter', sans-serif;
                font-weight: 700;
                letter-spacing: -0.02em;
            }

            [data-testid="stMetricValue"] {
                font-family: 'Inter', sans-serif;
                font-weight: 600;
                font-feature-settings: "tnum" on, "lnum" on;
            }
            
            .stDataFrame {
                font-family: 'Inter', sans-serif;
                font-feature-settings: "tnum" on;
            }

            .block-container {
                padding-top: 2.5rem !important; 
                padding-bottom: 1rem !important;
                max-width: 100% !important;
            }
            
            header[data-testid="stHeader"] {
                height: 3rem !important;
            }

            .custom-header {
                display: flex;
                align-items: baseline;
                gap: 1rem;
                margin-bottom: 1rem;
                padding-bottom: 0.5rem;
            }
            .custom-header-title {
                font-size: 1.8rem;
                font-weight: 700;
                margin: 0;
                color: var(--text-color);
            }
            .custom-header-subtitle {
                font-size: 1rem;
                font-weight: 400;
                color: gray;
                margin: 0;
            }
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

st.markdown("""
    <div class="custom-header">
        <div class="custom-header-title">TRFolio</div>
    </div>
""", unsafe_allow_html=True)


def save_portfolio_weights(stocks_df: pd.DataFrame) -> None:
    """Calculate and save stock portfolio weights to CSV.

    Considers only stocks (crypto and ETFs are excluded upstream).
    Output columns: name, weight_%  — sorted descending by weight.
    """
    total_mv = stocks_df['market_value'].sum()
    if total_mv == 0:
        return

    weights = stocks_df[['name', 'market_value']].copy()
    weights['weight_%'] = (weights['market_value'] / total_mv * 100).round(2)
    weights = (
        weights[['name', 'weight_%']]
        .sort_values('weight_%', ascending=False)
        .reset_index(drop=True)
    )

    out = settings.portfolio_weights_path
    out.parent.mkdir(parents=True, exist_ok=True)
    weights.to_csv(out, index=False)

# ============================================================================
# 1. DATA LOADING (Global Cache)
# ============================================================================
@st.cache_resource
def init_data():
    """Load all base data from database."""
    con = get_db_connection()
    
    transactions = load_transactions(con)
    trades = load_trades(con)
    
    holdings = calculate_holdings(con)
    etf_holdings = calculate_etf_holdings(con)
    interest_data = calculate_interest_income(con)
    
    return con, transactions, trades, holdings, etf_holdings, interest_data

con, transactions, trades, holdings, etf_holdings, interest_data = init_data()

if holdings.empty and etf_holdings.empty and transactions.empty:
    st.warning("No data found. Please run import (main.py) first.")
    st.stop()

# ============================================================================
# 2. SIDEBAR & FILTERING
# ============================================================================

selected_year_str = render_sidebar(transactions)

if selected_year_str != "All Time":
    selected_year = int(selected_year_str)
    
    transactions_filtered = transactions[transactions['date'].dt.year == selected_year].copy()
    
    if not trades.empty:
        trades_filtered = trades[trades['sell_date'].dt.year == selected_year].copy()
    else:
        trades_filtered = pd.DataFrame()
else:
    selected_year = None
    transactions_filtered = transactions.copy()
    trades_filtered = trades.copy()

# ============================================================================
# 3. PRICE UPDATES & ENRICHMENT (Live Data)
# ============================================================================

if not holdings.empty:
    prices, currencies, _, tickers_used = load_current_prices_auto_currency(holdings['isin'].unique())
    sectors = fetch_sectors(tickers_used)
    
    holdings['current_price'] = holdings['isin'].map(prices)
    holdings['currency'] = holdings['isin'].map(currencies)
    holdings['ticker'] = holdings['isin'].map(tickers_used)
    holdings['sector'] = holdings['ticker'].map(sectors).fillna('Unknown')
    
    holdings['market_value'] = holdings['current_shares'] * holdings['current_price']
    holdings['unrealized_pnl'] = holdings['market_value'] - holdings['total_cost']
    holdings['unrealized_pnl_pct'] = holdings.apply(
        lambda x: (x['unrealized_pnl'] / x['total_cost'] * 100) if x['total_cost'] > 0 else 0, axis=1
    )

    stocks_holdings = holdings[holdings['is_crypto'] == 0].copy()
    crypto_holdings = holdings[holdings['is_crypto'] == 1].copy()
else:
    stocks_holdings = pd.DataFrame()
    crypto_holdings = pd.DataFrame()

if not etf_holdings.empty:
    etf_prices, etf_currencies, _, etf_tickers = load_current_prices_auto_currency(etf_holdings['isin'].unique())
    
    etf_holdings['current_price'] = etf_holdings['isin'].map(etf_prices)
    etf_holdings['currency'] = etf_holdings['isin'].map(etf_currencies)
    etf_holdings['ticker'] = etf_holdings['isin'].map(etf_tickers)
    
    etf_holdings['market_value'] = etf_holdings['current_shares'] * etf_holdings['current_price']
    etf_holdings['unrealized_pnl'] = etf_holdings['market_value'] - etf_holdings['total_cost']
    etf_holdings['unrealized_pnl_pct'] = etf_holdings.apply(
        lambda x: (x['unrealized_pnl'] / x['total_cost'] * 100) if x['total_cost'] > 0 else 0, axis=1
    )
else:
    etf_holdings = pd.DataFrame()

if settings.enable_portfolio_weights_export and not stocks_holdings.empty:
    save_portfolio_weights(stocks_holdings)

# ============================================================================
# 4. KPI CALCULATIONS
# ============================================================================
stock_returns = calculate_stock_returns(holdings, trades_filtered)
crypto_returns = calculate_crypto_returns(crypto_holdings)
etf_returns = calculate_etf_returns(etf_holdings)

# ============================================================================
# 5. MAIN VIEW (TABS)
# ============================================================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview",
    "Stocks",
    "Crypto",
    "ETFs",
    "Income",
    "Log"
])

with tab1:
    render_overview(
        stocks_holdings=stocks_holdings,
        crypto_holdings=crypto_holdings,
        etf_holdings=etf_holdings,
        interest_data=interest_data,
        all_holdings=holdings,
        transactions=transactions_filtered,
        trades=trades_filtered
    )

with tab2:
    render_stocks_deep_dive(
        stocks_holdings=stocks_holdings,
        trades=trades_filtered
    )

with tab3:
    render_crypto_deep_dive(
        crypto_holdings=crypto_holdings,
        transactions=transactions_filtered
    )

with tab4:
    render_etf_deep_dive(
        etf_holdings=etf_holdings,
        transactions=transactions_filtered
    )

with tab5:
    render_income_deep_dive(
        interest_data=interest_data,
        transactions=transactions_filtered,
        trades=trades_filtered
    )

with tab6:
    render_transaction_log(
        transactions=transactions_filtered
    )

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.caption(f"""
    Environment: {settings.db_path} | 
    Timeframe: {selected_year_str} | 
    ℹ️ Accounting Method: FIFO
""")
