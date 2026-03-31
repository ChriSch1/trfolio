"""
calculations.py - Portfolio Calculations

Profit/Loss, Returns, Realized Gains, etc.
"""
import pandas as pd

from src.config import settings

def calculate_stock_returns(holdings: pd.DataFrame, trades: pd.DataFrame) -> dict:
    """Calculate returns based on FIFO positions and trades."""
    
    # 1. Unrealized Stocks
    stocks = holdings[holdings['is_crypto'] == 0].copy()
    
    if stocks.empty:
        return _empty_return_dict()
    
    current_value = stocks['market_value'].sum()
    invested_current = stocks['total_cost'].sum()
        
    unrealized = current_value - invested_current
    unrealized_pct = (unrealized / invested_current * 100) if invested_current > 0 else 0
    
    # 2. Realized Trades for stocks
    realized_gains = 0.0
    invested_sold = 0.0  # FIX: Initialize variable

    # Filter trades for stocks
    if not trades.empty:
        if 'is_crypto' in trades.columns:
            stock_trades = trades[trades['is_crypto'] == 0].copy()
        else:
            stock_trades = trades.copy()
            
        realized_gains = stock_trades['realized_gain'].sum()
        
        # Calculate invested capital of sold positions
        if 'avg_buy_price' in stock_trades.columns and 'shares_sold' in stock_trades.columns:
            invested_sold = (stock_trades['avg_buy_price'] * stock_trades['shares_sold']).sum()

    total_gains = unrealized + realized_gains
    total_invested = invested_current + invested_sold
    total_return_pct = (total_gains / total_invested * 100) if total_invested > 0 else 0
    
    return {
        'value': current_value,
        'invested_current': invested_current,
        'invested_total': total_invested, # Return corrected total invested
        'unrealized': unrealized,
        'unrealized_pct': unrealized_pct,
        'realized_gains': realized_gains,
        'total_gains': total_gains,
        'total_return_pct': total_return_pct,
    }

def extract_sold_positions(trades: pd.DataFrame) -> list:
    """Format trades table for display."""
    if trades.empty:
        return []
    
    deals = []
    for _, row in trades.iterrows():
        deals.append({
            'Security': row.get('security_name', row['isin']),
            'Sell Date': row['sell_date'].strftime('%Y-%m-%d'),
            'Avg Holding (Days)': row.get('holding_period_days', 0),
            'Buy Price': row['avg_buy_price'],
            'Sell Price': row['sell_price'],
            'Shares': row['shares_sold'],
            'Total Profit': row['realized_gain'],
            'Return %': row['realized_gain_percent']
        })
    
    return sorted(deals, key=lambda x: x['Sell Date'], reverse=True)

def calculate_etf_returns(etf_holdings: pd.DataFrame) -> dict:
    """Calculate ETF portfolio returns."""
    if etf_holdings.empty:
        return _empty_return_dict_simple()
        
    current_value = etf_holdings['market_value'].sum()
    invested = etf_holdings['total_cost'].sum()
    unrealized = current_value - invested
    unrealized_pct = (unrealized / invested * 100) if invested > 0 else 0
    
    return {
        'value': current_value,
        'invested': invested,
        'unrealized': unrealized,
        'unrealized_pct': unrealized_pct,
    }

def calculate_crypto_returns(crypto_holdings: pd.DataFrame, transactions: pd.DataFrame = None) -> dict:
    """Calculate crypto portfolio returns."""
    if crypto_holdings.empty:
        return _empty_return_dict()
    
    current_value = crypto_holdings['market_value'].sum()
    invested_current = crypto_holdings['total_cost'].abs().sum()
    unrealized = current_value - invested_current
    unrealized_pct = (unrealized / invested_current * 100) if invested_current > 0 else 0
    
    # Calculate realized gains from crypto transactions
    realized_gains = 0.0
    invested_sold = 0.0
    
    if transactions is not None and not transactions.empty:
        # Filter for crypto sell events
        if 'is_crypto' in transactions.columns:
            crypto_sells = transactions[(transactions['is_crypto'] == 1) & 
                                       (transactions['event_type'] == 'sell')]
            if not crypto_sells.empty and 'realized_gain' in crypto_sells.columns:
                realized_gains = crypto_sells['realized_gain'].sum()
                if 'avg_buy_price' in crypto_sells.columns and 'shares_sold' in crypto_sells.columns:
                    invested_sold = (crypto_sells['avg_buy_price'] * crypto_sells['shares_sold'].abs()).sum()
    
    total_gains = unrealized + realized_gains
    total_invested = invested_current + invested_sold
    total_return_pct = (total_gains / total_invested * 100) if total_invested > 0 else 0
    
    return {
        'value': current_value,
        'invested_current': invested_current,
        'invested_total': total_invested,
        'unrealized': unrealized,
        'unrealized_pct': unrealized_pct,
        'realized_gains': realized_gains,
        'total_gains': total_gains,
        'total_return_pct': total_return_pct,
    }


def _empty_return_dict():
    return {'value': 0.0,
            'invested_current': 0.0,
            'invested_total': 0.0,
            'unrealized': 0.0,
            'unrealized_pct': 0.0,
            'realized_gains': 0.0,
            'total_gains': 0.0,
            'total_return_pct': 0.0}

def _empty_return_dict_simple():
    return {'value': 0.0,
            'invested': 0.0,
            'unrealized': 0.0,
            'unrealized_pct': 0.0}