"""
config_loader.py - Datenbank & Cache Management

Alle Funktionen für Datenbeschaffung aus DuckDB mit Streamlit Caching.
"""
import streamlit as st
import duckdb
import pandas as pd
from src.config import settings

@st.cache_resource
def get_db_connection():
    """Create cached DuckDB connection."""
    return duckdb.connect(str(settings.db_path), read_only=True)


@st.cache_data(ttl=settings.transaction_cache_ttl)
def load_transactions(_con):
    """Load all transactions from DuckDB."""
    # We construct a view where 'name' is the best available name (clean > original)
    # But we also keep 'original_name' if needed for debugging
    transactions = _con.execute("""
        SELECT 
            t.name as original_name,
            COALESCE(t.clean_name, t.name) as name, -- Use clean name for display
            t.clean_name,
            t.date, t.event_type, t.isin, t.ticker,
            t.unit_price, t.unit_amount, t.dividend_per_share,
            t.currency, t.exchange_rate, t.gross_amount, t.net_cash_flow,
            t.external_fee, t.foreign_tax, t.capital_tax, t.church_tax, t.soli_tax,
            t.is_crypto, t.details, t.created_at
        FROM transactions t
        ORDER BY date
    """).df()

    return transactions


@st.cache_data(ttl=settings.transaction_cache_ttl)
def calculate_holdings(_con):
    """Calculate current holdings from FIFO-positions table"""
    try:
        # We need to get the latest metadata (name, currency) for each ISIN
        # We also grab clean_name from the transaction history
        return _con.execute("""
            WITH latest_metadata AS (
                SELECT 
                    isin, 
                    name,
                    clean_name,
                    currency, 
                    is_crypto
                FROM transactions
                WHERE isin IS NOT NULL
                QUALIFY ROW_NUMBER() OVER (PARTITION BY isin ORDER BY date DESC, created_at DESC) = 1
            )
            SELECT 
                COALESCE(lm.clean_name, lm.name) as name, -- Prefer clean name
                p.isin,
                p.ticker,
                p.shares as current_shares,
                p.total_cost,
                p.avg_entry_price,
                lm.currency,
                lm.is_crypto
            FROM positions p
            LEFT JOIN latest_metadata lm ON p.isin = lm.isin
            WHERE p.shares > 0.0001
            ORDER BY p.total_cost DESC""").df()
    
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=settings.transaction_cache_ttl)
def load_trades(_con):
    """Lade die berechnete Trade-Historie (FIFO)."""
    try:
        df = _con.execute("""
            WITH latest_metadata AS (
                SELECT 
                    isin, name, clean_name, is_crypto
                FROM transactions
                WHERE isin IS NOT NULL
                QUALIFY ROW_NUMBER() OVER (PARTITION BY isin ORDER BY date DESC, created_at DESC) = 1
            )
            SELECT 
                t.*,
                COALESCE(lm.clean_name, lm.name) as security_name, -- Prefer clean name
                COALESCE(lm.is_crypto, 0) as is_crypto
            FROM trades t
            LEFT JOIN latest_metadata lm ON t.isin = lm.isin
            ORDER BY t.sell_date DESC
        """).df()
        
        if not df.empty:
            df['sell_date'] = pd.to_datetime(df['sell_date'])
            df['is_crypto'] = df['is_crypto'].astype(int)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=settings.transaction_cache_ttl)
def calculate_etf_holdings(_con):
    """Calculate current ETF holdings from transactions."""
    # Here MAX(clean_name) is tricky because if some are null it might behave oddly, 
    # but since we backfill, it should be fine. 
    # Safer: COALESCE(MAX(clean_name), MAX(name))
    return _con.execute("""
        SELECT 
            COALESCE(MAX(clean_name), MAX(name)) as name,
            isin,
            SUM(unit_amount) as current_shares,
            SUM(ABS(net_cash_flow)) as total_cost,
            MAX(currency) as currency
        FROM transactions
        WHERE event_type = 'etf_saving_plan'
        GROUP BY isin
        HAVING current_shares > 0.001
        ORDER BY total_cost DESC
    """).df()


@st.cache_data(ttl=settings.transaction_cache_ttl)
def calculate_interest_income(_con):
    """Calculate interest income by month."""
    # Interest usually doesn't have an ISIN or ticker, so name is just 'Zinsen' or similar
    # We don't really need clean_name logic here, but let's keep it consistent
    return _con.execute("""
        SELECT 
            DATE_TRUNC('month', date) as month, 
            MAX(name) as name, -- Usually 'Interest'
            SUM(net_cash_flow) as net_interest,
            SUM(COALESCE(capital_tax, 0)) as taxes,
            currency
        FROM transactions
        WHERE event_type = 'interest'
        GROUP BY DATE_TRUNC('month', date), currency
        ORDER BY month DESC
    """).df()