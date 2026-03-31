"""
data_loader.py - Externe Datenbeschaffung

ISIN→Ticker Mapping, Kurse, Sektor-Daten, Wechselkurse
"""
import streamlit as st
import yfinance as yf
import pandas as pd
from src.ticker_mapper import batch_isin_to_ticker, isin_to_yf_ticker, batch_fetch_sectors
from src.config import settings


@st.cache_data(ttl=3600)
def build_ticker_mapping(holdings_df: pd.DataFrame) -> dict:
    """Build ISIN→ticker mapping using config + OpenFIGI."""
    mapping = {}
    in_memory_cache = {}
    
    # Step 1: Add crypto tokens
    mapping.update(settings.crypto_tokens)
    
    # Step 2: Add manual ISIN overrides from config
    mapping.update(settings.isin_overrides)
    
    # Step 3: Lookup remaining ISINs
    isins_to_lookup = []
    for isin in holdings_df['isin'].unique():
        if isin not in mapping:
            isins_to_lookup.append(isin)
    
    if isins_to_lookup:
        if len(isins_to_lookup) > 1:
            new_mappings = batch_isin_to_ticker(isins_to_lookup, cache=in_memory_cache)
        else:
            ticker = isin_to_yf_ticker(isins_to_lookup[0], cache=in_memory_cache)
            new_mappings = {isins_to_lookup[0]: ticker} if ticker else {}
        
        mapping.update(new_mappings)
    
    return mapping


@st.cache_data(ttl=3600)
def get_exchange_rates_all() -> dict:
    """Fetch all relevant exchange rates to EUR."""
    rates = {
        'USD': 1.0,
        'EUR': 1.0,
        'GBP': 1.0,
        'CHF': 1.0,
        'JPY': 1.0,
        'CAD': 1.0,
        'AUD': 1.0,
    }
    
    try:
        eurusd = yf.Ticker("EURUSD=X")
        data = eurusd.history(period='1d')
        if not data.empty:
            rates['USD'] = 1 / data['Close'].iloc[-1]
    except:
        rates['USD'] = 1.10  # Fallback
    
    try:
        eurgbp = yf.Ticker("EURGBP=X")
        data = eurgbp.history(period='1d')
        if not data.empty:
            rates['GBP'] = 1 / data['Close'].iloc[-1]
    except:
        rates['GBP'] = 1.17  # Fallback
    
    try:
        eurchf = yf.Ticker("EURCHF=X")
        data = eurchf.history(period='1d')
        if not data.empty:
            rates['CHF'] = 1 / data['Close'].iloc[-1]
    except:
        rates['CHF'] = 1.05  # Fallback
    
    try:
        eurjpy = yf.Ticker("EURJPY=X")
        data = eurjpy.history(period='1d')
        if not data.empty:
            rates['JPY'] = 1 / data['Close'].iloc[-1]
    except:
        rates['JPY'] = 0.0067  # Fallback
    
    try:
        eurcad = yf.Ticker("EURCAD=X")
        data = eurcad.history(period='1d')
        if not data.empty:
            rates['CAD'] = 1 / data['Close'].iloc[-1]
    except:
        rates['CAD'] = 0.67  # Fallback
    
    try:
        euraud = yf.Ticker("EURAUD=X")
        data = euraud.history(period='1d')
        if not data.empty:
            rates['AUD'] = 1 / data['Close'].iloc[-1]
    except:
        rates['AUD'] = 0.62  # Fallback
    
    return rates


def detect_ticker_currency(isin: str) -> tuple:
    """Detect currency of a security from yfinance."""
    try:
        # Check config overrides FIRST
        ticker_to_use = settings.isin_overrides.get(isin, isin)
        ticker = yf.Ticker(ticker_to_use)
        data = ticker.history(period='1d')
        
        if data.empty:
            return None, None, None
        
        price = data['Close'].iloc[-1]
        info = ticker.info
        currency = info.get('currency', None)
        
        if not currency:
            currency = info.get('financialCurrency', None)
        
        if not currency:
            exchange = info.get('exchange', '').upper()
            currency_by_exchange = {
                'NYSE': 'USD', 'NASDAQ': 'USD',
                'XETRA': 'EUR', 'XETR': 'EUR',
                'LSE': 'GBP', 'SIX': 'CHF',
                'XJPX': 'JPY', 'TSE': 'CAD', 'ASX': 'AUD',
            }
            currency = currency_by_exchange.get(exchange, 'USD')
        
        return price, currency, ticker.info.get('symbol')
    
    except Exception as e:
        return None, None, None


def fetch_price_for_ticker(ticker: str) -> tuple:
    """Fetch price and currency for a given ticker.
    
    Used for ticker overrides.
    Returns (price, currency) tuple
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='1d')
        
        if hist.empty:
            return None, None
        
        price = hist['Close'].iloc[-1]
        info = stock.info
        currency = info.get('currency') or info.get('financialCurrency') or 'USD'
        
        return price, currency
    except Exception:
        return None, None


def convert_to_eur(amount: float, from_currency: str, exchange_rates: dict = None) -> float:
    """Convert amount from any currency to EUR."""
    if from_currency == 'EUR' or from_currency is None:
        return amount
    
    if exchange_rates is None:
        exchange_rates = get_exchange_rates_all()
    
    rate = exchange_rates.get(from_currency, 1.0)
    return amount * rate


def load_current_prices_auto_currency(holdings_isin_list: list) -> tuple:
    """Load current prices and auto-detect currency from yfinance.
    
    Uses manual ticker overrides from config if available.
    
    Args:
        holdings_isin_list: List of ISINs to fetch prices for
    
    Returns:
        Tuple of (prices, currencies, exchange_rates, tickers_used)
    """
    prices = {}
    currencies = {}
    tickers_used = {}
    exchange_rates = get_exchange_rates_all()
    
    for isin in holdings_isin_list:
        # Check config overrides FIRST (manual_ticker_overrides take priority!)
        if isin in settings.isin_overrides:
            ticker = settings.isin_overrides[isin]
            price, currency = fetch_price_for_ticker(ticker)
            tickers_used[isin] = ticker
        else:
            # Fall back to automatic detection
            price, currency, ticker = detect_ticker_currency(isin)
            tickers_used[isin] = ticker
        
        if price is not None:
            price_eur = convert_to_eur(price, currency, exchange_rates)
            prices[isin] = price_eur
            currencies[isin] = currency if currency else 'UNKNOWN'
        else:
            prices[isin] = None
            currencies[isin] = 'ERROR'
    
    return prices, currencies, exchange_rates, tickers_used


@st.cache_data(ttl=3600)
def fetch_sectors(ticker_mapping: dict) -> dict:
    """Fetch sector information for all tickers."""
    sector_cache = {}
    sectors = batch_fetch_sectors(ticker_mapping, cache=sector_cache)
    return sectors