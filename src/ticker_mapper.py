"""ISIN to Yahoo Finance ticker mapping using OpenFIGI API."""
import time
import logging
import requests
import yfinance as yf

from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Map OpenFIGI exchange codes to Yahoo Finance suffixes
EXCHANGE_MAP = {
    "US": "", "UN": "", "UW": "", "UR": "", "UQ": "",
    "GY": ".DE", "GR": ".DE", "GF": ".F",
    "LN": ".L", "PA": ".PA", "AS": ".AS", "MI": ".MI", "SW": ".SW",
    "JP": ".T", "HK": ".HK", "SS": ".SS", "KS": ".KS",
    "CN": ".TO", "AU": ".AX",
}


def isin_to_yf_ticker(isin: str, cache: Dict[str, str] = None) -> Optional[str]:
    """
    Convert ISIN to Yahoo Finance ticker using OpenFIGI API.

    Args:
        isin: International Securities Identification Number
        cache: Optional dict to cache results (prevents redundant API calls)

    Returns:
        Yahoo Finance ticker symbol or None if not found
    """
    if cache and isin in cache:
        logger.debug(f"Cache hit: {isin} -> {cache[isin]}")
        return cache[isin]

    try:
        url = "https://api.openfigi.com/v3/mapping"
        headers = {"Content-Type": "application/json"}
        payload = [{"idType": "ID_ISIN", "idValue": isin}]

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data or "data" not in data[0]:
            logger.warning(f"No ticker found for ISIN {isin}")
            return None

        results = data[0]["data"]

        primary = [r for r in results if r.get("isPrimary")]
        result = primary[0] if primary else results[0]

        ticker = result.get("ticker")
        exchange = result.get("exchCode")

        if not ticker:
            return None

        suffix = EXCHANGE_MAP.get(exchange, f".{exchange}")
        yf_symbol = f"{ticker}{suffix}" if suffix else ticker

        if cache is not None:
            cache[isin] = yf_symbol

        logger.info(f"Mapped {isin} -> {yf_symbol} (exchange: {exchange})")
        return yf_symbol

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for ISIN {isin}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error mapping ISIN {isin}: {e}")
        return None


def batch_isin_to_ticker(isins: list[str], cache: Dict[str, str] = None) -> Dict[str, str]:
    """
    Convert multiple ISINs to tickers in one batch call.

    Args:
        isins: List of ISINs to convert
        cache: Optional cache dict

    Returns:
        Dict mapping ISIN -> ticker
    """
    mapping = {}

    uncached_isins = []
    if cache:
        for isin in isins:
            if isin in cache:
                mapping[isin] = cache[isin]
            else:
                uncached_isins.append(isin)
    else:
        uncached_isins = isins

    if not uncached_isins:
        return mapping

    try:
        url = "https://api.openfigi.com/v3/mapping"
        headers = {"Content-Type": "application/json"}
        payload = [{"idType": "ID_ISIN", "idValue": isin} for isin in uncached_isins]

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        for i, isin in enumerate(uncached_isins):
            if i >= len(data) or "data" not in data[i]:
                continue

            results = data[i]["data"]
            if not results:
                continue

            primary = [r for r in results if r.get("isPrimary")]
            result = primary[0] if primary else results[0]

            ticker = result.get("ticker")
            exchange = result.get("exchCode")

            if ticker:
                suffix = EXCHANGE_MAP.get(exchange, f".{exchange}")
                yf_symbol = f"{ticker}{suffix}" if suffix else ticker
                mapping[isin] = yf_symbol

                if cache is not None:
                    cache[isin] = yf_symbol

        logger.info(f"Batch mapped {len(mapping)}/{len(isins)} ISINs")
        return mapping

    except Exception as e:
        logger.error(f"Batch mapping failed: {e}")
        for isin in uncached_isins:
            ticker = isin_to_yf_ticker(isin, cache)
            if ticker:
                mapping[isin] = ticker

        return mapping


def get_or_fetch_ticker(
    isin: str,
    config=None,
    db_connection=None,
    rate_limit_delay: float = 0.5,
    cache: dict = None
) -> Optional[str]:
    """
    Resolve ticker using 3-tier fallback strategy.

    1. Check config.isin_overrides (manual mappings)
    2. Check database ticker_mappings (previous lookups)
    3. Call OpenFIGI API (with rate limit protection)
    """
    from src.storage import PortfolioStorage

    if config and hasattr(config, 'isin_overrides'):
        if isin in config.isin_overrides:
            logger.debug(f"Tier 1 (Config): {isin} -> {config.isin_overrides[isin]}")
            return config.isin_overrides[isin]

    if db_connection:
        try:
            storage = PortfolioStorage(db_path=":memory:")
            storage.con = db_connection
            cached_ticker = storage.get_ticker_from_db(isin)
            if cached_ticker:
                logger.debug(f"Tier 2 (DB Cache): {isin} -> {cached_ticker}")
                return cached_ticker
        except Exception as e:
            logger.warning(f"Failed to check DB cache for {isin}: {e}")

    try:
        logger.info(f"Tier 3 (API): Fetching ticker for {isin}...")
        ticker = isin_to_yf_ticker(isin, cache=cache)

        if ticker and db_connection:
            try:
                storage = PortfolioStorage(db_path=":memory:")
                storage.con = db_connection
                storage.store_ticker_mapping(isin, ticker, source="openfigi")
                logger.debug(f"Cached {isin} -> {ticker} in database")
            except Exception as e:
                logger.warning(f"Failed to cache ticker for {isin}: {e}")

        if ticker:
            time.sleep(rate_limit_delay)

        return ticker

    except Exception as e:
        logger.warning(f"Failed to fetch ticker for {isin} via API: {e}")
        return None


def batch_get_tickers(
    isins: list,
    config=None,
    db_connection=None,
    rate_limit_delay: float = 0.5
) -> dict:
    """Resolve tickers for multiple ISINs using 3-tier strategy."""
    mapping = {}
    for isin in isins:
        mapping[isin] = get_or_fetch_ticker(
            isin,
            config=config,
            db_connection=db_connection,
            rate_limit_delay=rate_limit_delay
        )
    return mapping


def batch_fetch_sectors(tickers: dict, cache: dict = None) -> dict:
    """
    Fetch sectors for multiple tickers efficiently.

    Args:
        tickers: Dict mapping ISIN -> ticker (e.g., {'US0378331005': 'AAPL'})
        cache: Optional cache dict

    Returns:
        Dict mapping ticker -> sector
    """
    sectors = {}
    uncached = []

    if cache:
        for isin, ticker in tickers.items():
            if ticker in cache:
                sectors[ticker] = cache[ticker]
            else:
                uncached.append((isin, ticker))
    else:
        uncached = list(tickers.items())

    for isin, ticker in uncached:
        try:
            stock = yf.Ticker(ticker)
            sector = stock.info.get("sector", "Unknown")

            if cache is not None:
                cache[ticker] = sector

            sectors[ticker] = sector
            logger.info(f"Fetched sector for {ticker}: {sector}")
        except Exception as e:
            logger.error(f"Error fetching sector for {ticker} ({isin}): {e}")
            sectors[ticker] = "Unknown"

    return sectors
