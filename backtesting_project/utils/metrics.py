"""
Performance metrics calculation for backtest results.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


def calculate_metrics(trades_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate comprehensive performance metrics from trades DataFrame.
    
    Args:
        trades_df: DataFrame with trade history including pips_gained, status, etc.
    
    Returns:
        Dictionary containing all calculated metrics
    
    Raises:
        ValueError: If trades_df is empty
    """
    if trades_df.empty:
        return {
            'Total Trades': 0,
            'Net Pips': 0.0,
            'Win Rate': 0.0,
            'Message': 'No trades to analyze'
        }
    
    # Basic statistics
    total_pips = trades_df['pips_gained'].sum()
    win_trades = trades_df[trades_df['pips_gained'] > 0]
    loss_trades = trades_df[trades_df['pips_gained'] <= 0]
    
    total_trades = len(trades_df)
    win_count = len(win_trades)
    loss_count = len(loss_trades)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    
    # Average win/loss
    avg_win = win_trades['pips_gained'].mean() if not win_trades.empty else 0
    avg_loss = loss_trades['pips_gained'].mean() if not loss_trades.empty else 0
    
    # Largest win/loss
    largest_win = win_trades['pips_gained'].max() if not win_trades.empty else 0
    largest_loss = loss_trades['pips_gained'].min() if not loss_trades.empty else 0
    
    # Consecutive wins/losses
    max_con_wins, max_con_losses = calculate_consecutive(trades_df['pips_gained'])
    
    # Drawdown calculation
    trades_df = trades_df.copy()
    trades_df['cumulative_pips'] = trades_df['pips_gained'].cumsum()
    trades_df['peak'] = trades_df['cumulative_pips'].cummax()
    trades_df['drawdown'] = trades_df['cumulative_pips'] - trades_df['peak']
    max_drawdown = trades_df['drawdown'].min()
    
    # Profit factor
    gross_profit = win_trades['pips_gained'].sum() if not win_trades.empty else 0
    gross_loss = abs(loss_trades['pips_gained'].sum()) if not loss_trades.empty else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
    
    # Expectancy
    expectancy = (total_pips / total_trades) if total_trades > 0 else 0
    
    # Build metrics dictionary
    metrics = {
        'Total Trades': total_trades,
        'Winning Trades': win_count,
        'Losing Trades': loss_count,
        'Win Rate (%)': round(win_rate, 2),
        'Net Pips': round(total_pips, 2),
        'Average Win': round(avg_win, 2),
        'Average Loss': round(avg_loss, 2),
        'Largest Win': round(largest_win, 2),
        'Largest Loss': round(largest_loss, 2),
        'Profit Factor': round(profit_factor, 2) if profit_factor != float('inf') else 'Infinity',
        'Expectancy (pips/trade)': round(expectancy, 2),
        'Max Drawdown': round(max_drawdown, 2),
        'Max Consecutive Wins': max_con_wins,
        'Max Consecutive Losses': max_con_losses
    }
    
    return metrics


def calculate_consecutive(pips_series: pd.Series) -> tuple:
    """
    Calculate maximum consecutive wins and losses.
    
    Args:
        pips_series: Series of pips gained/lost per trade
    
    Returns:
        Tuple of (max_consecutive_wins, max_consecutive_losses)
    """
    max_con_wins = 0
    max_con_losses = 0
    cur_wins = 0
    cur_losses = 0
    
    for pips in pips_series:
        if pips > 0:
            cur_wins += 1
            cur_losses = 0
            max_con_wins = max(max_con_wins, cur_wins)
        else:
            cur_losses += 1
            cur_wins = 0
            max_con_losses = max(max_con_losses, cur_losses)
    
    return max_con_wins, max_con_losses


def calculate_monthly_summary(trades_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate monthly performance summary.
    
    Args:
        trades_df: DataFrame with trade history including entry_time, pips_gained, status
    
    Returns:
        DataFrame with monthly aggregated metrics
    
    Raises:
        ValueError: If trades_df is empty or missing required columns
    """
    if trades_df.empty:
        return pd.DataFrame()
    
    # Ensure entry_time is datetime and set as index
    df = trades_df.copy()
    
    if 'entry_time' not in df.columns:
        if df.index.name == 'entry_time':
            df = df.reset_index()
        else:
            raise ValueError("Missing 'entry_time' column")
    
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df = df.set_index('entry_time')
    df = df.sort_index()
    
    # Monthly aggregation
    monthly_summary = df.resample('ME').agg({
        'pips_gained': ['sum', 'count', 'mean'],
        'status': lambda x: (x == 'TP_HIT').sum()
    })
    
    # Flatten column names
    monthly_summary.columns = ['Total_Pips', 'Trade_Count', 'Avg_Pips', 'TP_Hits']
    
    # Calculate win rate per month
    monthly_summary['Win_Rate_%'] = (
        monthly_summary['TP_Hits'] / monthly_summary['Trade_Count'] * 100
    ).fillna(0)
    
    # Calculate profit factor per month
    monthly_profit = df[df['pips_gained'] > 0].resample('ME')['pips_gained'].sum()
    monthly_loss = df[df['pips_gained'] < 0].resample('ME')['pips_gained'].sum().abs()
    monthly_summary['Profit_Factor'] = (monthly_profit / monthly_loss).replace(
        [float('inf'), -float('inf')], 
        np.nan
    )
    
    # Calculate max drawdown per month
    df['cumulative_pips'] = df['pips_gained'].cumsum()
    df['peak'] = df['cumulative_pips'].cummax()
    df['drawdown'] = df['cumulative_pips'] - df['peak']
    monthly_dd = df.resample('ME')['drawdown'].min()
    monthly_summary['Max_Drawdown'] = monthly_dd
    
    # Clean up - remove months with no trades
    monthly_summary = monthly_summary[monthly_summary['Trade_Count'] > 0]
    
    return monthly_summary


def print_metrics(metrics: Dict[str, Any], title: str = "Performance Metrics") -> None:
    """
    Print metrics in a formatted way.
    
    Args:
        metrics: Dictionary of metrics to print
        title: Title for the metrics display
    """
    print(f"\n{'='*50}")
    print(f"{title:^50}")
    print('='*50)
    
    for key, value in metrics.items():
        print(f"{key:<30}: {value}")
    
    print('='*50)
