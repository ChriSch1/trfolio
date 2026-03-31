# 🔧 Manual Ticker Overrides Guide

## Overview

When yfinance cannot automatically resolve an ISIN to the correct ticker, you can manually add mappings in `src/config_sample.py`.

## How to Add Overrides

Edit `src/config_sample.py` and add your mappings to the `isin_overrides` dictionary:

```python
isin_overrides: Dict[str, str] = Field(default_factory=lambda: {
    "IE00B4L5Y983": "EUNL.DE",  # MSCI World ETF (XETRA)
    "IE00BD45KH83": "IBC3.DE",   # MSCI EM ETF (XETRA)
})
```

## Common ETF Examples

### iShares ETFs

| ETF Name | ISIN | Ticker (XETRA) | Ticker (US) | Region |
|----------|------|-----------------|-------------|--------|
| MSCI World | IE00B4L5Y983 | EUNL.DE | EUN1.L | Global |
| MSCI EM | IE00BD45KH83 | IBC3.DE | IEMG | Emerging Markets |
| MSCI World Quality | IE000A2PWHL2 | D8HV.DE | QVAL | Global |
| MSCI World Value | IE00BZY5W825 | D8FN.DE | VALX | Global |
| MSCI World Dividend | IE00B0F63284 | EUNL.DE | UDIV | Global |

### Vanguard ETFs

| ETF Name | ISIN | Ticker (XETRA) | Region |
|----------|------|-----------------|--------|
| FTSE All-World UCITS | IE00B4L5Y983 | VWRL.DE | Global |
| FTSE Developed World | IE00BK5BQT80 | VHVG.DE | Developed |
| EM Markets | IE00BZ56RQ86 | VFEM.DE | Emerging |

### Lyxor ETFs

| ETF Name | ISIN | Ticker (XETRA) | Region |
|----------|------|-----------------|--------|
| MSCI World | LU1829220028 | LYMWL.DE | Global |
| MSCI EM | LU1832721189 | LYEM.DE | Emerging |

## How It Works

1. **Priority System:**
   - Manual overrides from `src/config_sample.py` (highest priority)
   - Automatic detection via OpenFIGI API
   - Error/None if neither works

2. **Automatic Lookup Flow:**
   ```
   ISIN
     ↓
   Check config overrides? → Yes: Use override ticker
     ↓ No
   Automatic OpenFIGI lookup
     ↓
   Fetch price + currency from yfinance
   ```

3. **Persistence:**
   - All overrides are stored in `src/config_sample.py`
   - Changes persist across app restarts
   - Can be version-controlled on Git

## Finding the Right Ticker

### Method 1: Search yfinance

```bash
python
>>> import yfinance as yf
>>> stock = yf.Ticker('EUNL.DE')
>>> stock.info['longName']
'iShares MSCI World UCITS ETF (Acc)'
```

### Method 2: Check official ETF provider

- iShares: https://www.ishares.com
- Vanguard: https://www.vanguard.com
- Lyxor: https://www.lyxor.com

### Method 3: Search on Trading Platform

- XETRA (German): https://www.xetra.com
- London Stock Exchange: https://www.londonstockexchange.com
- NASDAQ: https://www.nasdaq.com

## Exchange Codes

When searching for tickers, use these exchange suffixes:

| Exchange | Suffix | Currency | Country |
|----------|--------|----------|----------|
| XETRA | .DE | EUR | Germany |
| Frankfurt | .F | EUR | Germany |
| Stuttgart | .SG | EUR | Germany |
| London | .L | GBP | UK |
| NASDAQ | (none) | USD | US |
| NYSE | (none) | USD | US |
| SIX | .SW | CHF | Switzerland |

## Verification

After adding an override, verify it works:

```python
# In app_refactored.py console:
from src.config_sample import settings

# Check overrides loaded
print(settings.isin_overrides)
# {'IE00B4L5Y983': 'EUNL.DE', ...}

# Check ticker is fetching correctly
from src.dashboard.data_loader import fetch_price_for_ticker
price, currency = fetch_price_for_ticker('EUNL.DE')
print(f"Price: {price} {currency}")
# Price: 127.45 EUR
```

## Dashboard Display

The footer shows how many overrides are active:

```
🔧 Manual Overrides: 3 active
```

## Troubleshooting

### Override Not Working

1. **Check syntax:**
   ```python
   # ❌ Wrong
   "IE00B4L5Y983" : "EUNL.DE"  # Extra space before colon
   
   # ✅ Correct
   "IE00B4L5Y983": "EUNL.DE"
   ```

2. **Verify ISIN in your holdings:**
   ```bash
   # Check your actual ISINs
   python
   >>> import duckdb
   >>> con = duckdb.connect('./Trade Republic/portfolio/portfolio.duckdb')
   >>> con.execute("SELECT DISTINCT isin FROM transactions").df()
   ```

3. **Restart app:**
   ```bash
   streamlit run app_refactored.py
   ```

### Ticker Not Found by yfinance

If even the override ticker doesn't work:

1. Verify ticker is correct: `yf.Ticker('EUNL.DE').info`
2. Try alternative exchange: EUNL.DE vs MSWD.L vs EUN1.L
3. Check if ticker is tradeable on your exchange

## Contributing

If you find good ISIN→Ticker mappings, consider:

1. Adding them to `src/config_sample.py`
2. Submitting a pull request
3. Documenting in this guide

## See Also

- [yfinance Documentation](https://github.com/ranaroussi/yfinance)
- [OpenFIGI API](https://www.openfigi.com/api)
- [XETRA ETF Search](https://www.xetra.com)
