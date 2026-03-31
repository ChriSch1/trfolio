import uuid
import pandas as pd
import logging

from datetime import datetime
from typing import List, Dict, Any

from src.config import settings
from src.stock_split_handler import apply_stock_splits

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(self, db_connection):
        self.con = db_connection

    def calculate_fifo(self):
        """Recalculate all derived tables from scratch based on raw transactions."""
        logger.info("Starting FIFO recalculation...")

        self.con.execute("DELETE FROM positions")
        self.con.execute("DELETE FROM lots")
        self.con.execute("DELETE FROM trades")

        tx_df = self.con.execute("""
            SELECT * FROM transactions
            WHERE event_type IN ('buy', 'sell')
            AND isin IS NOT NULL
            ORDER BY date ASC, created_at ASC
        """).df()

        if tx_df.empty:
            logger.info("No transactions found.")
            return

        if settings.stock_splits:
            tx_df = apply_stock_splits(tx_df, settings.stock_splits)

        # Key: ISIN, Value: list of open lots
        open_lots: Dict[str, List[Dict[str, Any]]] = {}

        trades_to_insert = []
        positions_to_insert = []

        for _, tx in tx_df.iterrows():
            isin = tx['isin']
            event = tx['event_type'].lower()

            if isin not in open_lots:
                open_lots[isin] = []

            if event == 'buy':
                # Cost basis including fees for realistic performance tracking
                total_cost = tx['gross_amount'] + (tx['external_fee'] or 0)
                cost_per_share = total_cost / tx['unit_amount'] if tx['unit_amount'] > 0 else 0

                new_lot = {
                    'lot_id': str(uuid.uuid4()),
                    'isin': isin,
                    'buy_date': tx['date'],
                    'shares_original': tx['unit_amount'],
                    'shares_remaining': tx['unit_amount'],
                    'price_per_share': tx['unit_price'],
                    'cost_per_share_incl_fees': cost_per_share
                }
                open_lots[isin].append(new_lot)

            elif event == 'sell':
                shares_to_sell = tx['unit_amount']
                sell_price = tx['unit_price']

                realized_cost_basis = 0.0
                shares_sold_total = 0.0
                weighted_buy_price_sum = 0.0
                weighted_holding_days_sum = 0.0

                sell_date_dt = pd.to_datetime(tx['date'])

                while shares_to_sell > 0.000001 and open_lots[isin]:
                    current_lot = open_lots[isin][0]

                    take_shares = min(shares_to_sell, current_lot['shares_remaining'])

                    lot_buy_date = pd.to_datetime(current_lot['buy_date'])
                    sell_date = pd.to_datetime(tx['date'])
                    days_diff = max((sell_date - lot_buy_date).days, 0)

                    weighted_holding_days_sum += take_shares * days_diff
                    realized_cost_basis += take_shares * current_lot['cost_per_share_incl_fees']
                    weighted_buy_price_sum += take_shares * current_lot['price_per_share']

                    current_lot['shares_remaining'] -= take_shares
                    shares_to_sell -= take_shares
                    shares_sold_total += take_shares

                    if current_lot['shares_remaining'] < 0.000001:
                        open_lots[isin].pop(0)

                if shares_sold_total > 0:
                    avg_buy_price_raw = weighted_buy_price_sum / shares_sold_total
                    avg_holding_days = int(weighted_holding_days_sum / shares_sold_total)
                    trade_revenue_net = (shares_sold_total * sell_price) - (tx['external_fee'] or 0)

                    pnl = trade_revenue_net - realized_cost_basis
                    pnl_percent = (pnl / realized_cost_basis * 100) if realized_cost_basis > 0 else 0

                    trades_to_insert.append({
                        'trade_id': str(uuid.uuid4()),
                        'isin': isin,
                        'sell_date': tx['date'],
                        'shares_sold': shares_sold_total,
                        'sell_price': sell_price,
                        'avg_buy_price': avg_buy_price_raw,
                        'realized_gain': pnl,
                        'realized_gain_percent': (pnl / realized_cost_basis * 100) if realized_cost_basis > 0 else 0,
                        'holding_period_days': avg_holding_days
                    })

        for isin, lots in open_lots.items():
            total_shares = sum(l['shares_remaining'] for l in lots)
            if total_shares > 0.000001:
                total_cost_basis = sum(l['shares_remaining'] * l['cost_per_share_incl_fees'] for l in lots)
                avg_entry = total_cost_basis / total_shares

                positions_to_insert.append({
                    'isin': isin,
                    'ticker': None,
                    'shares': total_shares,
                    'avg_entry_price': avg_entry,
                    'total_cost': total_cost_basis,
                    'current_value': 0.0,
                    'last_updated': datetime.now()
                })

                for lot in lots:
                    self.con.execute("""
                        INSERT INTO lots (lot_id, isin, buy_date, shares_original, shares_remaining, price_per_share, cost_per_share_incl_fees)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, [
                        lot['lot_id'], lot['isin'], lot['buy_date'],
                        lot['shares_original'], lot['shares_remaining'],
                        lot['price_per_share'], lot['cost_per_share_incl_fees']
                    ])

        if trades_to_insert:
            df_trades = pd.DataFrame(trades_to_insert)
            self.con.execute("INSERT INTO trades SELECT * FROM df_trades")

        if positions_to_insert:
            df_pos = pd.DataFrame(positions_to_insert)
            self.con.execute("""
                CREATE TEMP TABLE temp_pos AS SELECT * FROM df_pos;
                INSERT INTO positions
                SELECT t.isin, tm.ticker, t.shares, t.avg_entry_price, t.total_cost, 0.0, t.last_updated
                FROM temp_pos t
                LEFT JOIN ticker_mappings tm ON t.isin = tm.isin;
                DROP TABLE temp_pos;
            """)

        logger.info(f"FIFO recalculation done: {len(positions_to_insert)} positions, {len(trades_to_insert)} trades.")
