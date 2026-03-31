"""
components/transaction_log.py - Transaction History Tab
"""
import streamlit as st
import pandas as pd
from src.dashboard.theme import get_active_theme, is_minimal

def render_transaction_log(transactions: pd.DataFrame,
                           THEME=get_active_theme()) -> None:
    """
    Render the Transaction Log tab.
    """
    st.header("Transaction History")
    
    if transactions.empty:
        st.info("No transactions found.")
        return

    # Filter columns for cleaner view
    display_tx = transactions[[
        'date', 'event_type', 'name', 'isin', 'unit_amount', 'unit_price', 'net_cash_flow', 'currency'
    ]].sort_values('date', ascending=False).copy()
    
    display_tx.columns = [
        'Date', 'Type', 'Security', 'ISIN', 'Units', 'Price', 'Net Amount', 'Currency'
    ]
    
    # Helper for Cash Flow coloring
    def color_cash_flow(val):
        # Inflows (Dividends, Sales) = Teal
        if val > 0: return f'color: {THEME["success"]}; font-weight: bold'
        # Outflows (Buys) = Neutral or slight Coral (usually buys are negative cash flow)
        if val < 0: return f'color: {THEME["primary"]}' # Or THEME["neutral"]
        return ''

    st.dataframe(
        display_tx.style.format({
            'Date': lambda t: t.strftime('%Y-%m-%d'),
            'Units': '{:.4f}',
            'Price': '{:,.2f}',
            'Net Amount': '{:+,.2f}'
        }).applymap(color_cash_flow, subset=['Net Amount']),
        use_container_width=True,
        height=600 # Taller view for logs
    )
