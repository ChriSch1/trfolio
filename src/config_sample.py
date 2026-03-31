"""Application configuration with Pydantic Settings."""
import tomllib

from typing import Dict, List, Tuple
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Portfolio application settings loaded from environment or .env file."""
    
    # ============================================================================
    # Storage Paths
    # ============================================================================
    
    data_dir: Path = Path("./Trade Republic/invoices/")
    """Base directory for all portfolio data."""

    portfolio_dir: Path = Path("./Trade Republic/portfolio/")
    """Base directory where the database is/will be stored."""
    
    db_path: Path = Path("./Trade Republic/portfolio/portfolio.duckdb")
    """Path to DuckDB database file (computed from data_dir if not set)."""
    
    csv_path: Path = Path("./Trade Republic/portfolio/portfolio.csv")
    """Path to exported CSV file (computed from data_dir if not set)."""
    
    # ============================================================================
    # Input Paths (PDF Extraction)
    # ============================================================================
    
    invoice_dir: Path = Path("./Trade Republic")
    """Directory containing PDF invoices to extract."""

    # ============================================================================
    # Feature Flags
    # ============================================================================
    
    enable_initialization_portfolio: bool = False
    """When first time using this software and all files are already at the
    destination folder with which the software should work set this to True!"""
    
    enable_portfolio_weights_export: bool = True
    """Export current stock portfolio weights to CSV on each dashboard load.
    Only stocks are considered (no crypto, no ETFs)."""
    
    portfolio_weights_path: Path = Path("./Trade Republic/portfolio/holdings_weight.csv")
    """Output path for the portfolio weights CSV file.
    Only used when enable_portfolio_weights_export is True."""
    
    enable_csv_export: bool = True
    """Export to CSV file after each extraction."""
    
    enable_duplicate_detection: bool = True
    """Check for duplicate transactions before inserting."""
    
    enable_price_fetching: bool = True
    """Fetch current prices from yfinance for unrealized P&L calculation."""

    # ============================================================================
    # Crypto Token Mappings (for yfinance price fetching and PDF Extraction)
    # ============================================================================
    
    crypto_tokens: Dict[str, str] = Field(default_factory=lambda: {
        "bitcoin": "BTC-USD",
        "ethereum": "ETH-USD",
        "xrp": "XRP-USD",
        "solana": "SOL-USD",
        "cardano": "ADA-USD",
        "dogecoin": "DOGE-USD",
    })
    """Mapping of crypto names to yfinance tickers (use -USD suffix for USD pairs)."""

    # ============================================================================
    # Manual ISIN to Ticker Overrides
    # ============================================================================
    
    isin_overrides: Dict[str, str] = Field(default_factory=lambda: {
        "IE00B4L5Y983": "EUNL.DE",  # Beispiel: MSCI World ETF (XETRA)
        "IE00BD45KH83": "IBC3.DE",   # Beispiel: MSCI EM ETF (XETRA)
        "BTC": "BTC-EUR",          # Beispiel: Bitcoin
        "US02079K3059": "GOOGL",   # Beispiel:Alphabet Inc
    })
    """Manual ISIN to ticker mappings for securities where auto-detection fails.
    
    Use this when yfinance cannot find the correct ticker via ISIN lookup.
    These overrides take priority over automatic OpenFIGI resolution.
    
    Common examples:
    - MSCI World ETF: IE00B4L5Y983 → EUNL.DE (or MSWD.L, EUN1.DE)
    - MSCI EM ETF: IE00BD45KH83 → IBC3.DE (or IEMG)
    - Actual value indices: Use exchange-specific tickers
    """

        
    # ============================================================================
    # Corporate Actions (Stock Splits, Reverse Splits, etc.)
    # ============================================================================
    
    stock_splits: Dict[str, List[Tuple[str, float]]] = Field(default_factory=lambda: {
        # ISIN → [(date_str, split_ratio), ...]
        # Split ratio: new_shares = old_shares * ratio
        # Examples:
        "US5949181045": [("2024-06-10", 10)],  # NVIDIA 10:1 split
        # "US0311621009": [("2005-02-18", 2), ("2007-05-18", 2)],  # Multiple splits
    })
    """Historical stock splits and reverse splits by ISIN.
    
    Use this to adjust historical share counts for corporate actions.
    Each entry maps ISIN to list of (date, ratio) tuples:
    - date: When the split occurred (YYYY-MM-DD format)
    - ratio: Split multiplier (new_shares = old_shares * ratio)
    
    Examples:
    - Stock split 2:1 → ratio = 2 (e.g., NVIDIA 10:1 → ratio = 10)
    - Reverse split 1:10 → ratio = 0.1 (10 shares become 1 share)
    
    Important:
    - List dates in chronological order
    - These adjustments apply when loading holdings from CSV
    - The raw transaction data is not modified
    - Each split shifts the cost basis per share calculation
    
    Add entries for your holdings like:
        stock_splits = {
            "US5949181045": [("2024-06-10", 10)],  # NVIDIA
        }
    """

    
    # ============================================================================
    # Dashboard Settings
    # ============================================================================
    
    streamlit_theme: str = "dark"
    """Streamlit theme: 'light' or 'dark'."""
    
    price_cache_ttl: int = 3600
    """Time-to-live for cached price data in seconds (default 1 hour)."""
    
    transaction_cache_ttl: int = 300
    """Time-to-live for cached transaction data in seconds (default 5 minutes)."""
    
    
    # ============================================================================
    # Logging
    # ============================================================================
    
    log_level: str = "INFO"
    """Logging level: DEBUG, INFO, WARNING, ERROR."""
    
    # ============================================================================
    # Pydantic Settings Config
    # ============================================================================
    
    model_config = SettingsConfigDict(
        env_prefix="PORTFOLIO_",  # env vars like PORTFOLIO_DATA_DIR
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def __init__(self, **kwargs):
        """Initialize settings and compute derived paths."""
        super().__init__(**kwargs)
        
        # Compute database and CSV paths if not explicitly set
        # Database files will be placed next to final destination of invoices
        if self.db_path is None:
            self.db_path = self.data_dir / "portfolio.duckdb"
        if self.csv_path is None:
            self.csv_path = self.data_dir / "portfolio.csv"
        
        # Ensure all directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.portfolio_dir.mkdir(parents=True, exist_ok=True)
        self.invoice_dir.mkdir(parents=True, exist_ok=True)
    
    def get_data_summary(self) -> dict:
        """Return summary of configured paths for logging/debugging."""
        return {
            "data_dir": str(self.data_dir),
            "portfolio_dir": str(self.portfolio_dir),
            "db_path": str(self.db_path),
            "csv_path": str(self.csv_path),
            "invoice_dir": str(self.invoice_dir),
            "cache_ttl_prices": f"{self.price_cache_ttl}s",
            "cache_ttl_transactions": f"{self.transaction_cache_ttl}s",
            "csv_export": self.enable_csv_export,
            "price_fetching": self.enable_price_fetching,
            "isin_overrides": len(self.isin_overrides),
            "stock_splits": len(self.stock_splits),
        }


# Singleton instance - load once and reuse throughout app
settings = Settings()
