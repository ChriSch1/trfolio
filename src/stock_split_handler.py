"""
stock_split_handler.py - Handle corporate actions (stock splits, etc.)

Applies historical stock split adjustments to share counts when loading holdings.
This ensures accurate position metrics after corporate restructuring events.

Usage:
    from src.stock_split_handler import apply_stock_splits
    
    # Load holdings
    holdings = load_holdings_from_csv()
    
    # Adjust for stock splits before calculations
    holdings = apply_stock_splits(holdings, stock_splits_config)
    
    # Now use holdings for P&L calculations
    calculate_stock_returns(holdings, transactions)
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple


def apply_stock_splits(
    data: pd.DataFrame,
    stock_splits: Dict[str, List[Tuple[str, float]]]
) -> pd.DataFrame:
    """
    Apply historical stock split adjustments to holdings or transactions.
    
    Correctly handles stock splits by:
    - Multiplying unit_amount by split ratio (more shares)
    - Dividing unit_price by split ratio (lower price per share)
    - Maintaining: unit_amount × unit_price = constant (invariant preserved)
    
    Example: 0.118948 shares @ €840.70 (before 10:1 split)
             → 1.18948 shares @ €84.07 (after 10:1 split)
             Check: 1.18948 × €84.07 ≈ €100.00 ✅
    
    Args:
        data: DataFrame containing either holdings or transactions
        stock_splits: Dict mapping ISIN → list of (date_str, ratio) tuples
    
    Returns:
        DataFrame with adjusted shares and prices
    """
    if data.empty or not stock_splits:
        return data
    
    # Work with a copy to avoid modifying original
    result = data.copy()
    
    # Determine if we're working with transactions or holdings
    is_transactions = 'date' in result.columns and 'unit_amount' in result.columns
    is_holdings = 'current_shares' in result.columns
    
    for isin, splits_list in stock_splits.items():
        # Find rows with this ISIN
        mask = result['isin'] == isin
        
        if not mask.any():
            continue
        
        # Sort splits chronologically
        sorted_splits = sorted(splits_list, key=lambda x: x[0])
        
        if is_transactions:
            # For transactions: adjust BOTH unit_amount AND unit_price
            # This maintains the cash flow invariant
            
            for split_date_str, split_ratio in sorted_splits:
                try:
                    split_date = pd.to_datetime(split_date_str)
                except Exception as e:
                    raise ValueError(f"Invalid split date format:\
                                    {split_date_str}. Use YYYY-MM-DD. Error: {e}")
                
                # Only adjust transactions that occurred BEFORE the split date
                tx_mask = mask & (result['date'] < split_date)
                
                if tx_mask.any():
                    # After a split: more shares at lower price
                    # Example: 1 @ €100 becomes 10 @ €10 (for 10:1 split)
                    
                    # Increase share count
                    result.loc[tx_mask, 'unit_amount'] = (
                        result.loc[tx_mask, 'unit_amount'] * split_ratio
                    )
                    
                    # Decrease price per share to maintain total value
                    result.loc[tx_mask, 'unit_price'] = (
                        result.loc[tx_mask, 'unit_price'] / split_ratio
                    )
        
        elif is_holdings:
            # For holdings: apply accumulated split ratio to share count
            total_ratio = 1.0
            for split_date_str, split_ratio in sorted_splits:
                total_ratio *= split_ratio
            
            result.loc[mask, 'current_shares'] = (
                result.loc[mask, 'current_shares'] * total_ratio
            )
    
    return result




def validate_stock_splits_config(stock_splits: Dict) -> bool:
    """
    Validate stock splits configuration.
    
    Args:
        stock_splits: Config dict to validate
    
    Returns:
        True if valid, raises ValueError otherwise
    """
    if not isinstance(stock_splits, dict):
        raise ValueError("stock_splits must be a dictionary")
    
    for isin, splits_list in stock_splits.items():
        if not isinstance(isin, str):
            raise ValueError(f"ISIN must be string, got {type(isin)}")
        
        if not isinstance(splits_list, list):
            raise ValueError(f"Splits for {isin} must be list, got {type(splits_list)}")
        
        for split_tuple in splits_list:
            if not isinstance(split_tuple, (tuple, list)) or len(split_tuple) != 2:
                raise ValueError(
                    f"Each split must be (date_str, ratio), got {split_tuple}"
                )
            
            date_str, ratio = split_tuple
            
            # Validate date format
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")
            
            # Validate ratio
            if not isinstance(ratio, (int, float)) or ratio <= 0:
                raise ValueError(f"Split ratio must be positive number, got {ratio}")
    
    return True
