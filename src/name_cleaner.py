"""
name_cleaner.py - Utilities to fetch and clean company names.

Uses Yahoo Finance to get official names and regex to strip legal suffixes.
"""
import re
import logging
import time
import yfinance as yf
from typing import Optional

logger = logging.getLogger(__name__)

def clean_name_string(text: str) -> str:
    """
    Cleans a company name by removing common legal suffixes and extra whitespace.
    Example: 'NVIDIA Corporation' -> 'NVIDIA'
    """
    if not text:
        return text

    suffixes = [
        r' Inc\.?$', r' Corp\.?$', r' Corporation', r' plc', r' PLC',
        r' SE', r' S\.A\.', r' AG', r' Ltd\.?$', r' Limited',
        r' N\.V\.', r' B\.V\.', r' Co\.?$', r' & Co\.?$',
        r' \(The\)', r' Common Stock', r' Class [AB]', r' Register.*',
        r' Shs', r' SpA', r' Group', r' Holdings', r' Hldgs',
        r' L\.P\.', r' S\.p\.A\.', r' S\.A\.S\.'
    ]

    cleaned = text
    for suffix in suffixes:
        cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.replace("UCITS ETF", "")
    cleaned = cleaned.replace("ETF", "")

    cleaned = cleaned.strip(' -,')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned

def fetch_clean_name(ticker: str) -> Optional[str]:
    """Fetch the short name from Yahoo Finance and clean it."""
    if not ticker:
        return None

    try:
        t = yf.Ticker(ticker)
        info = t.info
        raw_name = info.get('shortName') or info.get('longName')

        if raw_name:
            return clean_name_string(raw_name)

    except Exception as e:
        logger.debug(f"Failed to fetch name for {ticker}: {e}")

    return None

def get_or_fetch_clean_name(
    isin: str,
    ticker: str,
    db_connection=None,
    rate_limit_delay: float = 0.5
) -> Optional[str]:
    """
    Resolve clean name using 2-tier fallback strategy.

    1. Check database cache (name_mappings)
    2. Call Yahoo Finance API via ticker
    """
    if db_connection:
        try:
            res = db_connection.execute(
                "SELECT clean_name FROM name_mappings WHERE isin = ?", [isin]
            ).fetchone()

            if res and res[0]:
                logger.debug(f"Tier 1 (DB Cache): {isin} -> {res[0]}")
                return res[0]
        except Exception as e:
            logger.debug(f"Failed to check DB cache for name {isin}: {e}")

    if not ticker:
        return None

    try:
        clean_name = fetch_clean_name(ticker)

        if clean_name and db_connection:
            try:
                db_connection.execute(
                    "INSERT OR REPLACE INTO name_mappings (isin, clean_name, source) VALUES (?, ?, ?)",
                    [isin, clean_name, "yahoo"]
                )
                logger.debug(f"Cached name {isin} -> {clean_name}")
            except Exception as e:
                logger.warning(f"Failed to cache name for {isin}: {e}")

        if clean_name:
            time.sleep(rate_limit_delay)

        return clean_name

    except Exception as e:
        logger.warning(f"Failed to resolve name for {ticker}: {e}")
        return None
