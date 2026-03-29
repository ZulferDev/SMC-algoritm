"""
Visualization functions for backtest results and analysis.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter


def plot_equity_curve(trades_df: pd.DataFrame, 
                      title: str = "Equity Curve",
                      figsize: Tuple[int, int] = (14, 7),
                      save_path: Optional[str] = None) -> plt.Figure:
    """
    Plot cumulative pips equity curve from trades.
    
    Args:
        trades_df: DataFrame with trade history including pips_gained
        title: Chart title
        figsize: Figure size (width, height)
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Raises:
        ValueError: If trades_df is empty
    """
    if trades_df.empty:
        raise ValueError("Cannot plot equity curve: no trades data")
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Calculate cumulative pips
    trades_df = trades_df.copy()
    trades_df['cumulative_pips'] = trades_df['pips_gained'].cumsum()
    
    # Plot equity curve
    ax.plot(trades_df.index, trades_df['cumulative_pips'], 
            linewidth=2, color='blue', label='Cumulative Pips')
    
    # Add zero line
    ax.axhline(y=0, color='red', linestyle='--', linewidth=1, alpha=0.7)
    
    # Add drawdown shading
    trades_df['peak'] = trades_df['cumulative_pips'].cummax()
    trades_df['drawdown'] = trades_df['cumulative_pips'] - trades_df['peak']
    ax.fill_between(trades_df.index, trades_df['cumulative_pips'], 
                    trades_df['peak'], alpha=0.3, color='red', label='Drawdown')
    
    # Formatting
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Trade Number', fontsize=12)
    ax.set_ylabel('Pips', fontsize=12)
    ax.legend(loc='upper left' if trades_df['cumulative_pips'].iloc[-1] > 0 else 'lower left')
    ax.grid(True, alpha=0.3)
    
    # Add statistics text box
    stats_text = (
        f"Total Trades: {len(trades_df)}\n"
        f"Net Pips: {trades_df['cumulative_pips'].iloc[-1]:.1f}\n"
        f"Max Drawdown: {trades_df['drawdown'].min():.1f}"
    )
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)
    
    plt.tight_layout()
    
    # Save if path provided
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Chart saved to: {save_path}")
    
    return fig


def plot_signals_on_chart(data: pd.DataFrame, 
                          signals: pd.Series,
                          entry_trades: Optional[pd.DataFrame] = None,
                          exit_trades: Optional[pd.DataFrame] = None,
                          title: str = "Price Chart with Signals",
                          figsize: Tuple[int, int] = (16, 10),
                          show_ema: bool = True,
                          save_path: Optional[str] = None) -> plt.Figure:
    """
    Plot price chart with buy/sell signals and trade entries/exits.
    
    Args:
        data: OHLCV DataFrame
        signals: Series with signals (1=Buy, -1=Sell, 0=None)
        entry_trades: DataFrame with trade entries (optional)
        exit_trades: DataFrame with trade exits (optional)
        title: Chart title
        figsize: Figure size (width, height)
        show_ema: Whether to show EMA line if available
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    """
    fig, axes = plt.subplots(2, 1, figsize=figsize, gridspec_kw={'height_ratios': [3, 1]})
    
    # === Price Chart (Top) ===
    ax1 = axes[0]
    
    # Plot candlesticks (simplified version using lines)
    dates = data.index
    for i in range(len(data)):
        color = 'green' if data['Close'].iloc[i] >= data['Open'].iloc[i] else 'red'
        ax1.vlines(dates[i], data['Low'].iloc[i], data['High'].iloc[i], 
                   color=color, linewidth=1)
        ax1.vlines(dates[i], data['Open'].iloc[i], data['Close'].iloc[i], 
                   color=color, linewidth=3)
    
    # Plot EMA if available
    if show_ema and 'EMA' in data.columns:
        ax1.plot(dates, data['EMA'], color='orange', linewidth=2, label=f'EMA')
    
    # Plot signal markers
    buy_signals = signals[signals == 1]
    sell_signals = signals[signals == -1]
    
    if len(buy_signals) > 0:
        ax1.scatter(buy_signals.index, 
                   [data['Low'].loc[idx] * 0.9995 for idx in buy_signals.index],
                   marker='^', color='green', s=100, label='Buy Signal', zorder=5)
    
    if len(sell_signals) > 0:
        ax1.scatter(sell_signals.index,
                   [data['High'].loc[idx] * 1.0005 for idx in sell_signals.index],
                   marker='v', color='red', s=100, label='Sell Signal', zorder=5)
    
    # Plot trade entries if provided
    if entry_trades is not None and not entry_trades.empty:
        buy_entries = entry_trades[entry_trades['type'] == 'BUY']
        sell_entries = entry_trades[entry_trades['type'] == 'SELL']
        
        if not buy_entries.empty:
            ax1.scatter(buy_entries['entry_time'], buy_entries['entry_price'],
                       marker='^', color='darkgreen', s=150, linewidths=2, 
                       edgecolors='white', label='Entry (BUY)', zorder=6)
        
        if not sell_entries.empty:
            ax1.scatter(sell_entries['entry_time'], sell_entries['entry_price'],
                       marker='v', color='darkred', s=150, linewidths=2,
                       edgecolors='white', label='Entry (SELL)', zorder=6)
    
    # Plot trade exits if provided
    if exit_trades is not None and not exit_trades.empty:
        tp_exits = exit_trades[exit_trades['status'] == 'TP_HIT']
        sl_exits = exit_trades[exit_trades['status'] == 'SL_HIT']
        
        if not tp_exits.empty:
            ax1.scatter(tp_exits['exit_time'], tp_exits['exit_price'],
                       marker='o', color='gold', s=100, linewidths=2,
                       edgecolors='black', label='Exit (TP)', zorder=7)
        
        if not sl_exits.empty:
            ax1.scatter(sl_exits['exit_time'], sl_exits['exit_price'],
                       marker='x', color='black', s=100, linewidths=2,
                       label='Exit (SL)', zorder=7)
    
    ax1.set_title(title, fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price', fontsize=12)
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # === Volume/Signals Histogram (Bottom) ===
    ax2 = axes[1]
    
    # Create signal bars
    colors = ['green' if s == 1 else 'red' if s == -1 else 'gray' for s in signals]
    ax2.bar(signals.index, signals.abs(), color=colors, alpha=0.5, width=1)
    ax2.set_ylabel('Signal Strength', fontsize=10)
    ax2.set_xlabel('Date', fontsize=10)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(['None', 'Active'])
    ax2.grid(True, alpha=0.3)
    
    # Format x-axis
    if isinstance(data.index, pd.DatetimeIndex):
        ax1.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        ax2.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    
    # Save if path provided
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Chart saved to: {save_path}")
    
    return fig


def plot_monthly_performance(monthly_summary: pd.DataFrame,
                             title: str = "Monthly Performance",
                             figsize: Tuple[int, int] = (14, 8),
                             save_path: Optional[str] = None) -> plt.Figure:
    """
    Plot monthly performance summary.
    
    Args:
        monthly_summary: DataFrame with monthly aggregated metrics
        title: Chart title
        figsize: Figure size (width, height)
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    """
    if monthly_summary.empty:
        raise ValueError("Cannot plot: no monthly summary data")
    
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    
    # Subplot 1: Monthly Pips
    ax1 = axes[0, 0]
    colors = ['green' if p > 0 else 'red' for p in monthly_summary['Total_Pips']]
    ax1.bar(monthly_summary.index.strftime('%Y-%m'), monthly_summary['Total_Pips'], 
            color=colors, alpha=0.7)
    ax1.set_title('Monthly Net Pips')
    ax1.set_ylabel('Pips')
    ax1.tick_params(axis='x', rotation=45)
    ax1.axhline(y=0, color='black', linewidth=1)
    ax1.grid(True, alpha=0.3)
    
    # Subplot 2: Win Rate
    ax2 = axes[0, 1]
    ax2.bar(monthly_summary.index.strftime('%Y-%m'), monthly_summary['Win_Rate_%'],
            color='steelblue', alpha=0.7)
    ax2.set_title('Monthly Win Rate')
    ax2.set_ylabel('Win Rate (%)')
    ax2.tick_params(axis='x', rotation=45)
    ax2.axhline(y=50, color='orange', linestyle='--', linewidth=1)
    ax2.grid(True, alpha=0.3)
    
    # Subplot 3: Trade Count
    ax3 = axes[1, 0]
    ax3.bar(monthly_summary.index.strftime('%Y-%m'), monthly_summary['Trade_Count'],
            color='purple', alpha=0.7)
    ax3.set_title('Monthly Trade Count')
    ax3.set_ylabel('Number of Trades')
    ax3.tick_params(axis='x', rotation=45)
    ax3.grid(True, alpha=0.3)
    
    # Subplot 4: Profit Factor
    ax4 = axes[1, 1]
    pf_data = monthly_summary['Profit_Factor'].fillna(0)
    colors_pf = ['green' if pf > 1.5 else 'orange' if pf > 1 else 'red' for pf in pf_data]
    ax4.bar(monthly_summary.index.strftime('%Y-%m'), pf_data,
            color=colors_pf, alpha=0.7)
    ax4.set_title('Monthly Profit Factor')
    ax4.set_ylabel('Profit Factor')
    ax4.tick_params(axis='x', rotation=45)
    ax4.axhline(y=1, color='black', linewidth=1)
    ax4.axhline(y=1.5, color='green', linestyle='--', linewidth=1, alpha=0.5)
    ax4.grid(True, alpha=0.3)
    
    plt.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    # Save if path provided
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Chart saved to: {save_path}")
    
    return fig
