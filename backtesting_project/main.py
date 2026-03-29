"""
Main entry point for running the backtesting system.

This script demonstrates how to use the modular backtesting framework
to test the Breakout Strategy with Session Filter and Dynamic Support/Resistance
on Gold (XAUUSD) data.
"""

import pandas as pd
import matplotlib.pyplot as plt

from core import GoldPipEngine
from strategies import EMABreakoutStrategy
from data import prepare_data, remove_weekend_data, handle_missing_data
from utils import calculate_metrics, calculate_monthly_summary, print_metrics
from utils.visualization import plot_equity_curve, plot_monthly_performance
from config import CONFIG_MODERATE, BacktestConfig


def run_backtest(config: BacktestConfig = None,
                 symbol: str = "GC=F",
                 period: str = "2y",
                 lookback_period: int = 5,
                 min_touches: int = 2,
                 session_start: int = 13,
                 session_end: int = 17,
                 show_charts: bool = True):
    """
    Run complete backtest with specified configuration.
    
    Args:
        config: BacktestConfig object with parameters
        symbol: Trading symbol (default: GC=F for Gold)
        period: Data period (default: 2 years)
        lookback_period: Lookback for swing detection (default: 5)
        min_touches: Minimum touches for S/R confirmation (default: 2)
        session_start: Trading session start hour UTC (default: 13)
        session_end: Trading session end hour UTC (default: 17)
        show_charts: Whether to display charts
    
    Returns:
        Tuple of (metrics dict, trades DataFrame, monthly summary)
    """
    print("="*60)
    print("GOLD BACKTESTING SYSTEM - BREAKOUT STRATEGY")
    print("with Session Filter & Dynamic Support/Resistance")
    print("="*60)
    
    # Use default config if none provided
    if config is None:
        config = CONFIG_MODERATE
    
    # Validate configuration
    config.validate()
    
    print(f"\nConfiguration:")
    for key, value in config.to_dict().items():
        print(f"  {key}: {value}")
    
    print(f"\nStrategy Parameters:")
    print(f"  Lookback period: {lookback_period}")
    print(f"  Min touches for S/R: {min_touches}")
    print(f"  Trading session: {session_start:02d}:00 - {session_end:02d}:00 UTC")
    
    # ========== STEP 1: LOAD AND PREPARE DATA ==========
    print("\n" + "="*60)
    print("STEP 1: Loading Data...")
    print("="*60)
    
    try:
        data = prepare_data(
            source='yfinance',
            symbol=symbol,
            remove_weekends=True,
            handle_missing=True,
            validate=True
        )
        print(f"\nData loaded successfully: {len(data)} candles")
        print(f"Date range: {data.index.min()} to {data.index.max()}")
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None, None
    
    # ========== STEP 2: GENERATE SIGNALS ==========
    print("\n" + "="*60)
    print("STEP 2: Generating Trading Signals...")
    print("="*60)
    
    strategy = EMABreakoutStrategy(
        lookback_period=lookback_period,
        min_touches=min_touches,
        session_start_hour=session_start,
        session_end_hour=session_end
    )
    signals = strategy.generate_signals(data)
    
    # Analyze setup frequency
    setup_analysis = strategy.analyze_setups()
    print(f"\nSetup Analysis:")
    print(f"  Total candles: {setup_analysis['total_candles']}")
    print(f"  Candles in session: {setup_analysis['session_candles']}")
    print(f"  Swing highs detected: {setup_analysis['swing_points']['total_swing_highs']}")
    print(f"  Swing lows detected: {setup_analysis['swing_points']['total_swing_lows']}")
    print(f"  Resistance levels identified: {setup_analysis['support_resistance']['resistance_levels_identified']}")
    print(f"  Support levels identified: {setup_analysis['support_resistance']['support_levels_identified']}")
    print(f"  Total signals: {setup_analysis['signals']['total_signals']}")
    print(f"  Days with trades: {setup_analysis['daily_trading']['days_with_trades']}")
    
    # Show S/R levels summary
    sr_summary = strategy.get_sr_levels_summary()
    if sr_summary['resistance_levels']:
        print(f"\nTop 3 Resistance Levels:")
        for i, level in enumerate(sr_summary['resistance_levels'][:3], 1):
            print(f"  {i}. Price: {level['level']:.4f} | Touches: {level['touches']} | Strength: {level['strength']:.2f}")
    
    if sr_summary['support_levels']:
        print(f"\nTop 3 Support Levels:")
        for i, level in enumerate(sr_summary['support_levels'][:3], 1):
            print(f"  {i}. Price: {level['level']:.4f} | Touches: {level['touches']} | Strength: {level['strength']:.2f}")
    
    # ========== STEP 3: RUN BACKTEST ==========
    print("\n" + "="*60)
    print("STEP 3: Running Backtest...")
    print("="*60)
    
    engine = GoldPipEngine(data, pip_scale=config.pip_scale)
    
    engine.run_backtest(
        signals=signals,
        sl_pips=config.sl_pips,
        tp_pips=config.tp_pips,
        order_type=config.order_type,
        pending_dist_pips=config.pending_dist_pips,
        max_open_trades=config.max_open_trades,
        min_dist_between_orders=config.min_dist_between_orders
    )
    
    # ========== STEP 4: ANALYZE RESULTS ==========
    print("\n" + "="*60)
    print("STEP 4: Analyzing Results...")
    print("="*60)
    
    stats, trades_df = engine.get_analysis()
    
    if trades_df.empty:
        print("\nNo trades were executed. Consider adjusting strategy parameters.")
        print("Tips:")
        print("  - Reduce min_touches to find more S/R levels")
        print("  - Adjust lookback_period for more/less swing points")
        print("  - Widen trading session hours")
        return stats, trades_df, None
    
    # Calculate comprehensive metrics
    metrics = calculate_metrics(trades_df)
    print_metrics(metrics, title="BACKTEST PERFORMANCE METRICS")
    
    # Monthly summary
    monthly_summary = calculate_monthly_summary(trades_df)
    if not monthly_summary.empty:
        print("\nMonthly Summary (Last 12 months):")
        print(monthly_summary.tail(12).to_string())
    
    # Show last few trades
    print("\nLast 5 Trades:")
    print(trades_df[['entry_time', 'type', 'entry_price', 'exit_price', 'status', 'pips_gained']].tail())
    
    # ========== STEP 5: VISUALIZATION ==========
    if show_charts and len(trades_df) > 0:
        print("\n" + "="*60)
        print("STEP 5: Generating Charts...")
        print("="*60)
        
        # Plot equity curve
        try:
            fig1 = plot_equity_curve(
                trades_df,
                title=f"Equity Curve - {symbol} ({period})",
                save_path='reports/equity_curve.png'
            )
            print("✓ Equity curve saved to reports/equity_curve.png")
        except Exception as e:
            print(f"Could not plot equity curve: {e}")
        
        # Plot monthly performance
        if not monthly_summary.empty:
            try:
                fig2 = plot_monthly_performance(
                    monthly_summary,
                    title=f"Monthly Performance - {symbol}",
                    save_path='reports/monthly_performance.png'
                )
                print("✓ Monthly performance chart saved to reports/monthly_performance.png")
            except Exception as e:
                print(f"Could not plot monthly performance: {e}")
        
        # Show charts if in interactive environment
        plt.show()
    
    return metrics, trades_df, monthly_summary


if __name__ == "__main__":
    # Run backtest with default settings
    metrics, trades, monthly = run_backtest(
        config=CONFIG_MODERATE,
        symbol="GC=F",
        period="2y",
        lookback_period=5,      # Swing detection lookback
        min_touches=2,          # Minimum touches for S/R
        session_start=13,       # London-NY overlap start (13:00 UTC)
        session_end=17,         # London-NY overlap end (17:00 UTC)
        show_charts=True
    )
    
    # Example of custom configuration
    # custom_config = BacktestConfig(
    #     sl_pips=150,
    #     tp_pips=450,
    #     max_open_trades=1,
    #     min_dist_between_orders=150,
    #     pending_dist_pips=25
    # )
    # metrics, trades, monthly = run_backtest(
    #     config=custom_config,
    #     lookback_period=3,      # More sensitive swing detection
    #     min_touches=1,          # Less strict S/R confirmation
    #     session_start=8,        # Wider session (London open)
    #     session_end=20          # Through NY close
    # )
