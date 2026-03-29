"""
Main backtesting engine for Gold/XAUUSD trading strategies.
Supports multi-order management with distance validation.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from .models import Trade, PendingOrder


class GoldPipEngine:
    """
    Backtesting engine for Gold (XAUUSD) trading strategies.
    
    Features:
        - Multi-order support (multiple concurrent trades)
        - Pending order management (STOP and LIMIT orders)
        - Distance validation between orders
        - Individual SL/TP per trade
        - Detailed performance metrics
    
    Attributes:
        data: OHLCV DataFrame with datetime index
        pip_scale: Pip scale for XAUUSD (default 0.1 = $0.10 movement)
        trades: List of completed trades
        active_trades: List of currently open trades
        pending_order: Current pending order waiting to be triggered
    """
    
    def __init__(self, data: pd.DataFrame, pip_scale: float = 0.1):
        """
        Initialize the backtesting engine.
        
        Args:
            data: DataFrame with OHLCV data, indexed by datetime
            pip_scale: Pip value scale (0.1 for standard XAUUSD)
        
        Raises:
            ValueError: If required columns are missing from data
        """
        # Validate input data
        required_columns = ['Open', 'High', 'Low', 'Close']
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        self.data = data.copy()
        self.pip_scale = pip_scale
        self.trades: List[Trade] = []
        self.active_trades: List[Trade] = []
        self.pending_order: Optional[PendingOrder] = None
        
        # Validate pip_scale
        if pip_scale <= 0:
            raise ValueError("pip_scale must be positive")
    
    def _calculate_pips(self, entry: float, exit: float, direction: str) -> float:
        """
        Calculate profit/loss in pips.
        
        Args:
            entry: Entry price
            exit: Exit price
            direction: 'BUY' or 'SELL'
        
        Returns:
            Profit/loss in pips
        """
        diff = exit - entry
        if direction == 'SELL':
            diff = -diff
        return diff / self.pip_scale
    
    def _check_pending_trigger(self, pending: PendingOrder, 
                                curr_high: float, curr_low: float, 
                                curr_open: float) -> Tuple[bool, float]:
        """
        Check if a pending order should be triggered.
        
        Args:
            pending: Pending order to check
            curr_high: Current candle high
            curr_low: Current candle low
            curr_open: Current candle open
        
        Returns:
            Tuple of (triggered: bool, fill_price: float)
        """
        triggered = False
        fill_price = pending.price
        
        if pending.is_buy():
            if pending.is_stop() and curr_high >= pending.price:
                triggered = True
                fill_price = curr_open if curr_open > pending.price else pending.price
            elif pending.is_limit() and curr_low <= pending.price:
                triggered = True
                fill_price = curr_open if curr_open < pending.price else pending.price
        
        elif pending.is_sell():
            if pending.is_stop() and curr_low <= pending.price:
                triggered = True
                fill_price = curr_open if curr_open < pending.price else pending.price
            elif pending.is_limit() and curr_high >= pending.price:
                triggered = True
                fill_price = curr_open if curr_open > pending.price else pending.price
        
        return triggered, fill_price
    
    def _check_trade_exit(self, trade: Trade, curr_high: float, 
                          curr_low: float, curr_open: float) -> Tuple[Optional[float], Optional[str]]:
        """
        Check if a trade should be exited (SL or TP hit).
        
        Args:
            trade: Active trade to check
            curr_high: Current candle high
            curr_low: Current candle low
            curr_open: Current candle open
        
        Returns:
            Tuple of (exit_price: float or None, status: str or None)
        """
        exit_price = None
        status = None
        
        if trade.type == 'BUY':
            # Check SL first (priority)
            if curr_low <= trade.sl_price:
                exit_price = trade.sl_price if curr_open >= trade.sl_price else curr_open
                status = 'SL_HIT'
            # Check TP
            elif curr_high >= trade.tp_price:
                exit_price = trade.tp_price if curr_open <= trade.tp_price else curr_open
                status = 'TP_HIT'
        
        elif trade.type == 'SELL':
            # Check SL first (priority)
            if curr_high >= trade.sl_price:
                exit_price = trade.sl_price if curr_open <= trade.sl_price else curr_open
                status = 'SL_HIT'
            # Check TP
            elif curr_low <= trade.tp_price:
                exit_price = trade.tp_price if curr_open >= trade.tp_price else curr_open
                status = 'TP_HIT'
        
        return exit_price, status
    
    def run_backtest(self, 
                     signals: pd.Series,
                     sl_pips: int,
                     tp_pips: int,
                     order_type: str = 'STOP',
                     pending_dist_pips: int = 0,
                     max_open_trades: int = 2,
                     min_dist_between_orders: int = 100) -> None:
        """
        Run the backtest with given parameters.
        
        Args:
            signals: Series of trading signals (1=Buy, -1=Sell, 0=None)
            sl_pips: Stop loss in pips
            tp_pips: Take profit in pips
            order_type: 'STOP' or 'LIMIT' for pending orders
            pending_dist_pips: Distance from close to place pending order (in pips)
            max_open_trades: Maximum number of concurrent open trades
            min_dist_between_orders: Minimum distance between order entries (in pips)
        
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate parameters
        if sl_pips <= 0 or tp_pips <= 0:
            raise ValueError("SL and TP must be positive values")
        if max_open_trades < 1:
            raise ValueError("max_open_trades must be at least 1")
        if order_type not in ['STOP', 'LIMIT']:
            raise ValueError("order_type must be 'STOP' or 'LIMIT'")
        
        print(f"Backtest Multi-Order ({order_type})...")
        print(f"  Max Trades: {max_open_trades}")
        print(f"  Min Distance: {min_dist_between_orders} pips")
        print(f"  SL: {sl_pips} pips, TP: {tp_pips} pips")
        
        # Convert pips to price distances
        sl_dist_price = sl_pips * self.pip_scale
        tp_dist_price = tp_pips * self.pip_scale
        pending_dist_price = pending_dist_pips * self.pip_scale
        min_dist_price = min_dist_between_orders * self.pip_scale
        
        # Main backtest loop - bar by bar
        for i in range(1, len(self.data)):
            curr_time = self.data.index[i]
            curr_open = self.data['Open'].iloc[i]
            curr_high = self.data['High'].iloc[i]
            curr_low = self.data['Low'].iloc[i]
            
            # PHASE 1: Check pending order trigger and validate distance
            if self.pending_order is not None and len(self.active_trades) < max_open_trades:
                triggered, fill_price = self._check_pending_trigger(
                    self.pending_order, curr_high, curr_low, curr_open
                )
                
                if triggered:
                    # Validate distance from existing trades
                    is_distance_valid = True
                    for trade in self.active_trades:
                        dist = abs(fill_price - trade.entry_price)
                        if dist < min_dist_price:
                            is_distance_valid = False
                            break
                    
                    # Execute trade if distance is valid
                    if is_distance_valid:
                        trade_type = 'BUY' if self.pending_order.is_buy() else 'SELL'
                        
                        # Calculate individual SL/TP
                        if trade_type == 'BUY':
                            sl = fill_price - sl_dist_price
                            tp = fill_price + tp_dist_price
                        else:
                            sl = fill_price + sl_dist_price
                            tp = fill_price - tp_dist_price
                        
                        new_trade = Trade(
                            entry_time=curr_time,
                            entry_price=fill_price,
                            type=trade_type,
                            sl_price=sl,
                            tp_price=tp,
                            sl_pips=sl_pips,
                            tp_pips=tp_pips
                        )
                        
                        self.active_trades.append(new_trade)
                        self.pending_order = None
            
            # PHASE 2: Check exits for all active trades
            for trade in self.active_trades[:]:  # Iterate over copy to allow removal
                exit_price, status = self._check_trade_exit(
                    trade, curr_high, curr_low, curr_open
                )
                
                if exit_price is not None:
                    trade.exit_time = curr_time
                    trade.exit_price = exit_price
                    trade.status = status
                    trade.pips_gained = self._calculate_pips(
                        trade.entry_price, trade.exit_price, trade.type
                    )
                    
                    self.trades.append(trade)
                    self.active_trades.remove(trade)
            
            # PHASE 3: Create new pending orders if slots available
            if len(self.active_trades) < max_open_trades:
                signal = signals.iloc[i - 1]  # Signal from previous candle
                prev_close = self.data['Close'].iloc[i - 1]
                
                if signal != 0:
                    if signal == 1:  # Buy signal
                        full_type = f'BUY_{order_type}'
                        if order_type == 'STOP':
                            order_price = prev_close + pending_dist_price
                        else:  # LIMIT
                            order_price = prev_close - pending_dist_price
                    elif signal == -1:  # Sell signal
                        full_type = f'SELL_{order_type}'
                        if order_type == 'STOP':
                            order_price = prev_close - pending_dist_price
                        else:  # LIMIT
                            order_price = prev_close + pending_dist_price
                    
                    self.pending_order = PendingOrder(
                        create_time=curr_time,
                        type=full_type,
                        price=order_price,
                        sl_pips=sl_pips,
                        tp_pips=tp_pips
                    )
    
    def get_analysis(self) -> Tuple[Dict[str, Any], pd.DataFrame]:
        """
        Analyze backtest results and calculate performance metrics.
        
        Returns:
            Tuple of (statistics dictionary, trades DataFrame)
        
        Raises:
            ValueError: If no trades were executed
        """
        if not self.trades:
            return {
                'Total Trades': 0,
                'Net Pips': '0.0',
                'Win Rate': '0.00%',
                'Message': 'Tidak ada trade yang terjadi.'
            }, pd.DataFrame()
        
        # Convert trades to DataFrame
        df_trades = pd.DataFrame([t.to_dict() for t in self.trades])
        
        # Basic statistics
        total_pips = df_trades['pips_gained'].sum()
        win_trades = df_trades[df_trades['pips_gained'] > 0]
        loss_trades = df_trades[df_trades['pips_gained'] <= 0]
        win_rate = len(win_trades) / len(df_trades) * 100 if len(df_trades) > 0 else 0
        
        # Consecutive wins/losses
        max_con_wins = 0
        max_con_losses = 0
        cur_wins = 0
        cur_losses = 0
        
        for pips in df_trades['pips_gained']:
            if pips > 0:
                cur_wins += 1
                cur_losses = 0
                max_con_wins = max(max_con_wins, cur_wins)
            else:
                cur_losses += 1
                cur_wins = 0
                max_con_losses = max(max_con_losses, cur_losses)
        
        # Drawdown calculation
        df_trades['cumulative_pips'] = df_trades['pips_gained'].cumsum()
        df_trades['peak'] = df_trades['cumulative_pips'].cummax()
        df_trades['drawdown'] = df_trades['cumulative_pips'] - df_trades['peak']
        max_dd = df_trades['drawdown'].min()
        
        # Build statistics dictionary
        stats = {
            'Total Trades': len(df_trades),
            'Net Pips': f"{total_pips:.1f}",
            'Win Rate': f"{win_rate:.2f}%",
            'Avg Win': f"{win_trades['pips_gained'].mean():.1f}" if not win_trades.empty else "0",
            'Avg Loss': f"{loss_trades['pips_gained'].mean():.1f}" if not loss_trades.empty else "0",
            'Max Drawdown': f"{max_dd:.1f}",
            'Max Consec Wins': max_con_wins,
            'Max Consec Losses': max_con_losses
        }
        
        return stats, df_trades
    
    def get_active_trades_count(self) -> int:
        """Return the number of currently active trades."""
        return len(self.active_trades)
    
    def has_pending_order(self) -> bool:
        """Check if there's a pending order waiting."""
        return self.pending_order is not None
