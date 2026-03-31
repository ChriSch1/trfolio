import os
import duckdb
import logging
import pandas as pd

from pathlib import Path
from typing import List, Optional

from src.models import Record
from src.config import settings

logger = logging.getLogger(__name__)

# Columns that uniquely identify a transaction (business key).
# unit_price and unit_amount are included so that two legitimate partial
# fills for the same security on the same day at different prices (or
# different quantities) are NOT treated as duplicates of each other.
_UNIQUE_KEY_COLS = ["event_type", "isin", "date", "unit_price", "unit_amount"]


class PortfolioStorage:
    def __init__(self, db_path: str="data/portfolio.duckdb"):
        self.db_path = Path(db_path)
        self.con = duckdb.connect(str(self.db_path))
        self._ensure_table()
        self._ensure_ticker_mappings_table()
        self._ensure_name_mappings_table()
        self._ensure_reporting_tables()

    def _ensure_table(self):
        """Create transactions table if it doesn't exist and run schema migrations."""
        try:
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    name VARCHAR,
                    date DATE,
                    event_type VARCHAR,
                    isin VARCHAR,
                    ticker VARCHAR,
                    unit_price DOUBLE,
                    unit_amount DOUBLE,
                    dividend_per_share DOUBLE,
                    currency VARCHAR,
                    exchange_rate DOUBLE,
                    gross_amount DOUBLE,
                    net_cash_flow DOUBLE,
                    external_fee DOUBLE,
                    foreign_tax DOUBLE,
                    capital_tax DOUBLE,
                    church_tax DOUBLE,
                    soli_tax DOUBLE,
                    is_crypto BOOLEAN,
                    details VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            columns = self.con.execute("PRAGMA table_info(transactions)").fetchall()
            col_names = [col[1] for col in columns]

            if 'clean_name' not in col_names:
                logger.info("Migrating database: Adding 'clean_name' column...")
                self.con.execute("ALTER TABLE transactions ADD COLUMN clean_name VARCHAR")

            self._migrate_add_unique_constraint()
            self._migrate_extend_unique_key()

        except Exception as e:
            logger.error(f"Error ensuring transaction table: {e}")

    def _migrate_add_unique_constraint(self):
        """One-time migration: deduplicate existing rows and recreate the
        transactions table with a UNIQUE constraint on (event_type, isin, date).

        DuckDB does not support adding a UNIQUE constraint via ALTER TABLE, so
        the migration recreates the table.  A sentinel column
        'unique_constraint_applied' is added afterwards to mark completion so
        that the migration only ever runs once.
        """
        columns = self.con.execute("PRAGMA table_info(transactions)").fetchall()
        col_names = [col[1] for col in columns]

        if 'unique_constraint_applied' in col_names:
            return  # Migration already done — nothing to do.

        logger.info(
            "Migrating database: deduplicating transactions and adding "
            "UNIQUE constraint on (event_type, isin, date)..."
        )

        self.con.execute("""
            CREATE TABLE transactions_new (
                name VARCHAR,
                clean_name VARCHAR,
                date DATE,
                event_type VARCHAR,
                isin VARCHAR,
                ticker VARCHAR,
                unit_price DOUBLE,
                unit_amount DOUBLE,
                dividend_per_share DOUBLE,
                currency VARCHAR,
                exchange_rate DOUBLE,
                gross_amount DOUBLE,
                net_cash_flow DOUBLE,
                external_fee DOUBLE,
                foreign_tax DOUBLE,
                capital_tax DOUBLE,
                church_tax DOUBLE,
                soli_tax DOUBLE,
                is_crypto BOOLEAN,
                details VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                unique_constraint_applied BOOLEAN DEFAULT TRUE,
                UNIQUE (event_type, isin, date)
            )
        """)

        # Copy only the most-recently created row per business key.
        self.con.execute("""
            INSERT INTO transactions_new
            SELECT
                name, clean_name, date, event_type, isin, ticker,
                unit_price, unit_amount, dividend_per_share,
                currency, exchange_rate, gross_amount, net_cash_flow,
                external_fee, foreign_tax, capital_tax, church_tax,
                soli_tax, is_crypto, details, created_at, TRUE
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY event_type, isin, date
                        ORDER BY created_at DESC
                    ) AS rn
                FROM transactions
            ) ranked
            WHERE rn = 1
        """)

        self.con.execute("DROP TABLE transactions")
        self.con.execute("ALTER TABLE transactions_new RENAME TO transactions")

        removed = self.con.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]
        logger.info(
            f"Migration complete. Transactions table now has {removed} unique rows."
        )

    def _migrate_extend_unique_key(self):
        """One-time migration: replace the 3-column UNIQUE constraint
        (event_type, isin, date) with a 5-column key that also includes
        unit_price and unit_amount.

        This prevents two legitimate partial fills for the same security on
        the same day at different prices from being misidentified as
        duplicates.  A sentinel column 'unique_key_v2_applied' marks
        completion so the migration only ever runs once.
        """
        columns = self.con.execute("PRAGMA table_info(transactions)").fetchall()
        col_names = [col[1] for col in columns]

        if 'unique_key_v2_applied' in col_names:
            return  # Migration already done — nothing to do.

        logger.info(
            "Migrating database: extending UNIQUE constraint to "
            "(event_type, isin, date, unit_price, unit_amount)..."
        )

        self.con.execute("""
            CREATE TABLE transactions_new (
                name VARCHAR,
                clean_name VARCHAR,
                date DATE,
                event_type VARCHAR,
                isin VARCHAR,
                ticker VARCHAR,
                unit_price DOUBLE,
                unit_amount DOUBLE,
                dividend_per_share DOUBLE,
                currency VARCHAR,
                exchange_rate DOUBLE,
                gross_amount DOUBLE,
                net_cash_flow DOUBLE,
                external_fee DOUBLE,
                foreign_tax DOUBLE,
                capital_tax DOUBLE,
                church_tax DOUBLE,
                soli_tax DOUBLE,
                is_crypto BOOLEAN,
                details VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                unique_constraint_applied BOOLEAN DEFAULT TRUE,
                unique_key_v2_applied BOOLEAN DEFAULT TRUE,
                UNIQUE (event_type, isin, date, unit_price, unit_amount)
            )
        """)

        # Copy all existing rows — no deduplication needed here because the
        # old constraint already ensured uniqueness on the narrower key.
        # Rows that are identical on the new 5-column key (genuine duplicates)
        # are still deduplicated by keeping the most-recently created one.
        self.con.execute("""
            INSERT INTO transactions_new
            SELECT
                name, clean_name, date, event_type, isin, ticker,
                unit_price, unit_amount, dividend_per_share,
                currency, exchange_rate, gross_amount, net_cash_flow,
                external_fee, foreign_tax, capital_tax, church_tax,
                soli_tax, is_crypto, details, created_at, TRUE, TRUE
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY event_type, isin, date, unit_price, unit_amount
                        ORDER BY created_at DESC
                    ) AS rn
                FROM transactions
            ) ranked
            WHERE rn = 1
        """)

        self.con.execute("DROP TABLE transactions")
        self.con.execute("ALTER TABLE transactions_new RENAME TO transactions")

        total = self.con.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]
        logger.info(
            f"Migration complete. Transactions table now has {total} rows with "
            "extended unique key on (event_type, isin, date, unit_price, unit_amount)."
        )

    def _ensure_reporting_tables(self):
        """Create tables for calculated positions and history."""
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                isin VARCHAR PRIMARY KEY,
                ticker VARCHAR,
                shares DOUBLE,
                avg_entry_price DOUBLE,
                total_cost DOUBLE,
                current_value DOUBLE,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.con.execute("""
            CREATE TABLE IF NOT EXISTS lots (
                lot_id VARCHAR,
                isin VARCHAR,
                buy_date DATE,
                shares_original DOUBLE,
                shares_remaining DOUBLE,
                price_per_share DOUBLE,
                cost_per_share_incl_fees DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.con.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id VARCHAR PRIMARY KEY,
                isin VARCHAR,
                sell_date DATE,
                shares_sold DOUBLE,
                sell_price DOUBLE,
                avg_buy_price DOUBLE,
                realized_gain DOUBLE,
                realized_gain_percent DOUBLE,
                holding_period_days INTEGER
            )
        """)

    def _ensure_ticker_mappings_table(self):
        """Create ticker_mappings cache table if it doesn't exist."""
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS ticker_mappings (
                isin VARCHAR PRIMARY KEY,
                ticker VARCHAR NOT NULL,
                source VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _ensure_name_mappings_table(self):
        """Create name_mappings cache table if it doesn't exist."""
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS name_mappings (
                isin VARCHAR PRIMARY KEY,
                clean_name VARCHAR NOT NULL,
                source VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def find_duplicates(self, records: List[Record]) -> tuple[List[Record], List[int]]:
        """Identify duplicate records against existing transactions.

        Uses the business key (event_type, isin, date, unit_price, unit_amount)
        to detect records that are already stored.  This is a best-effort
        pre-flight check; the database UNIQUE constraint on that key is the
        authoritative guard.
        """
        if not records:
            return [], []

        new_records = []
        duplicate_indices = []

        for i, rec in enumerate(records):
            if rec.isin is None:
                exists = self.con.execute("""
                    SELECT COUNT(*) as cnt FROM transactions
                    WHERE event_type = ?
                    AND isin IS NULL
                    AND date = ?::DATE
                    AND unit_price IS NOT DISTINCT FROM ?
                    AND unit_amount IS NOT DISTINCT FROM ?
                """, [rec.event_type, rec.date, rec.unit_price, rec.unit_amount]).fetchone()
            else:
                exists = self.con.execute("""
                    SELECT COUNT(*) as cnt FROM transactions
                    WHERE event_type = ?
                    AND isin = ?
                    AND date = ?::DATE
                    AND unit_price IS NOT DISTINCT FROM ?
                    AND unit_amount IS NOT DISTINCT FROM ?
                """, [rec.event_type, rec.isin, rec.date, rec.unit_price, rec.unit_amount]).fetchone()

            if exists[0] == 0:
                new_records.append(rec)
            else:
                duplicate_indices.append(i)

        return new_records, duplicate_indices

    def append_records(self, records: List[Record]) -> int:
        """Append validated Pydantic records to DuckDB.

        Duplicate detection is done in two layers:
        1. Pre-flight: find_duplicates() filters already-stored records.
        2. DB-level: ON CONFLICT DO NOTHING ensures the UNIQUE constraint
           on (event_type, isin, date, unit_price, unit_amount) is the final
           guard against any race conditions or batch duplicates slipping
           through layer 1.
        """
        if not records:
            return 0

        new_records, duplicate_indices = self.find_duplicates(records)

        if new_records:
            df = pd.DataFrame([r.model_dump() for r in new_records])
            if 'clean_name' not in df.columns:
                df['clean_name'] = None

            self.con.execute("""
                INSERT INTO transactions (
                    name, clean_name, date, event_type, isin, ticker,
                    unit_amount, unit_price, dividend_per_share,
                    currency, exchange_rate, gross_amount, net_cash_flow,
                    external_fee, foreign_tax, capital_tax, church_tax,
                    soli_tax, is_crypto
                )
                SELECT
                    name, clean_name, date, event_type, isin, ticker,
                    unit_amount, unit_price, dividend_per_share,
                    currency, exchange_rate, gross_amount, net_cashflow,
                    external_fee, foreign_tax, capital_tax, church_tax,
                    soli_tax, is_crypto
                FROM df
                ON CONFLICT (event_type, isin, date, unit_price, unit_amount) DO NOTHING
            """)

        return {
            "total": len(records),
            "inserted": len(new_records),
            "duplicates": len(duplicate_indices),
            "duplicate_indices": duplicate_indices
        }

    def get_missing_tickers(self) -> List[str]:
        """Find all unique ISINs with missing tickers."""
        try:
            result = self.con.execute("""
                SELECT DISTINCT isin
                FROM transactions
                WHERE ticker IS NULL
                AND isin IS NOT NULL
                ORDER BY isin
            """).fetchall()
            return [row[0] for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get missing tickers: {e}")
            return []

    def get_missing_names(self) -> List[tuple]:
        """Find all unique ISINs with missing clean names where a ticker is available."""
        try:
            result = self.con.execute("""
                SELECT DISTINCT isin, ticker
                FROM transactions
                WHERE clean_name IS NULL
                AND isin IS NOT NULL
                AND ticker IS NOT NULL
                ORDER BY isin
            """).fetchall()
            return result if result else []
        except Exception as e:
            logger.error(f"Failed to get missing names: {e}")
            return []

    def backfill_missing_tickers(self, get_ticker_func, config, rate_limit_delay: float = 0.5) -> int:
        """Resolve missing tickers."""
        try:
            missing_isins = self.get_missing_tickers()
            if not missing_isins:
                logger.info("All records have tickers (no backfill needed)")
                return 0

            logger.info(f"Found {len(missing_isins)} ISINs with missing tickers")
            resolved_count = 0

            for isin in missing_isins:
                try:
                    logger.info(f"Resolving ticker for {isin}...")
                    ticker = get_ticker_func(
                        isin=isin,
                        config=config,
                        db_connection=self.con,
                        rate_limit_delay=rate_limit_delay,
                    )

                    if ticker:
                        self.con.execute(
                            "UPDATE transactions SET ticker = ? WHERE isin = ? AND ticker IS NULL",
                            [ticker, isin]
                        )
                        logger.info(f"  Updated {isin} -> {ticker}")
                        resolved_count += 1
                    else:
                        logger.warning(f"  Could not resolve {isin}")
                except Exception as e:
                    logger.error(f"  Error resolving {isin}: {e}")
                    continue
            return resolved_count
        except Exception as e:
            logger.error(f"Ticker backfill failed: {e}")
            return 0

    def backfill_missing_names(self, get_name_func, rate_limit_delay: float = 0.5) -> int:
        """Resolve missing clean_names using ticker."""
        try:
            missing = self.get_missing_names()
            if not missing:
                logger.info("All records have clean names (no backfill needed)")
                return 0

            logger.info(f"Found {len(missing)} ISINs with missing names")
            resolved_count = 0

            for isin, ticker in missing:
                try:
                    logger.info(f"Resolving name for {ticker} ({isin})...")
                    clean_name = get_name_func(
                        isin=isin,
                        ticker=ticker,
                        db_connection=self.con,
                        rate_limit_delay=rate_limit_delay
                    )

                    if clean_name:
                        self.con.execute(
                            "UPDATE transactions SET clean_name = ? WHERE isin = ?",
                            [clean_name, isin]
                        )
                        logger.info(f"  Updated {isin} -> {clean_name}")
                        resolved_count += 1
                    else:
                        logger.warning(f"  Could not resolve name for {ticker}")
                except Exception as e:
                    logger.error(f"  Error resolving name for {ticker}: {e}")
                    continue
            return resolved_count
        except Exception as e:
            logger.error(f"Name backfill failed: {e}")
            return 0

    def get_all_transactions(self) -> pd.DataFrame:
        """Retrieve all transactions."""
        return self.con.execute("""
            SELECT * FROM transactions
            ORDER BY date DESC, created_at DESC
        """).df()

    def export_to_csv(self, csv_path: str = "data/portfolio.csv"):
        """Export all transactions to CSV."""
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        df = self.get_all_transactions()
        df.to_csv(csv_path, index=False)
        return csv_path

    def get_summary(self) -> dict:
        """Get basic portfolio statistics."""
        return self.con.execute("""
            SELECT
                COUNT(*) as total_transactions,
                COUNT(DISTINCT isin) as unique_securities,
                MIN(date) as first_transaction,
                MAX(date) as last_transaction,
                SUM(CASE WHEN event_type = 'buy' THEN net_cash_flow ELSE 0 END) as total_invested,
                SUM(CASE WHEN event_type = 'dividend' THEN net_cash_flow ELSE 0 END) as total_dividends,
                SUM(CASE WHEN event_type = 'sell' THEN net_cash_flow ELSE 0 END) as total_proceeds
            FROM transactions
        """).fetchone()

    def get_ticker_from_db(self, isin: str) -> Optional[str]:
        """Lookup cached ticker from database."""
        result = self.con.execute(
            "SELECT ticker FROM ticker_mappings WHERE isin = ?",
            [isin]
        ).fetchone()
        return result[0] if result else None

    def store_ticker_mapping(self, isin: str, ticker: str, source: str = "manual"):
        """Cache a ticker mapping in the database."""
        self.con.execute(
            """INSERT OR REPLACE INTO ticker_mappings (isin, ticker, source)
            VALUES (?, ?, ?)""",
            [isin, ticker, source]
        )
        self.con.commit()

    def close(self):
        """Close the database connection."""
        self.con.close()


def save_portfolio_data(records: List[Record]) -> dict:
    """Convenience function: save records to DuckDB and export CSV."""
    storage = PortfolioStorage(settings.db_path)
    try:
        insert_stats = storage.append_records(records)
        csv_path = storage.export_to_csv(settings.csv_path)
        summary = storage.get_summary()
        return {
            "success": True,
            "total_processed": insert_stats["total"],
            "rows_inserted": insert_stats["inserted"],
            "duplicates_skipped": insert_stats["duplicates"],
            "duplicate_indices": insert_stats["duplicate_indices"],
            "db_path": str(storage.db_path),
            "csv_exported": str(csv_path) if csv_path else None,
            "summary": summary
        }
    finally:
        storage.close()
