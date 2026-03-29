"""
Configuration settings for backtesting.
Contains default parameters and constants.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BacktestConfig:
    """
    Configuration class for backtesting parameters.
    
    Attributes:
        pip_scale: Pip value scale (0.1 for standard XAUUSD)
        sl_pips: Default stop loss in pips
        tp_pips: Default take profit in pips
        order_type: Default order type ('STOP' or 'LIMIT')
        pending_dist_pips: Distance from close for pending orders
        max_open_trades: Maximum concurrent open trades
        min_dist_between_orders: Minimum distance between entries in pips
        symbol: Trading symbol
        timeframe: Data timeframe
    """
    pip_scale: float = 0.1
    sl_pips: int = 200
    tp_pips: int = 400
    order_type: str = 'STOP'
    pending_dist_pips: int = 35
    max_open_trades: int = 2
    min_dist_between_orders: int = 105
    symbol: str = "GC=F"
    timeframe: str = "1h"
    
    def validate(self) -> bool:
        """
        Validate configuration parameters.
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        if self.pip_scale <= 0:
            raise ValueError("pip_scale must be positive")
        if self.sl_pips <= 0:
            raise ValueError("sl_pips must be positive")
        if self.tp_pips <= 0:
            raise ValueError("tp_pips must be positive")
        if self.max_open_trades < 1:
            raise ValueError("max_open_trades must be at least 1")
        if self.min_dist_between_orders < 0:
            raise ValueError("min_dist_between_orders cannot be negative")
        if self.order_type not in ['STOP', 'LIMIT']:
            raise ValueError("order_type must be 'STOP' or 'LIMIT'")
        if self.pending_dist_pips < 0:
            raise ValueError("pending_dist_pips cannot be negative")
        
        return True
    
    def get_rr_ratio(self) -> float:
        """
        Calculate Risk:Reward ratio.
        
        Returns:
            Risk:Reward ratio (e.g., 2.0 for 1:2)
        """
        return self.tp_pips / self.sl_pips
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'pip_scale': self.pip_scale,
            'sl_pips': self.sl_pips,
            'tp_pips': self.tp_pips,
            'order_type': self.order_type,
            'pending_dist_pips': self.pending_dist_pips,
            'max_open_trades': self.max_open_trades,
            'min_dist_between_orders': self.min_dist_between_orders,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'rr_ratio': self.get_rr_ratio()
        }


# Default configurations for different strategies
CONFIG_CONSERVATIVE = BacktestConfig(
    sl_pips=100,
    tp_pips=200,
    max_open_trades=1,
    min_dist_between_orders=200,
    pending_dist_pips=20
)

CONFIG_MODERATE = BacktestConfig(
    sl_pips=200,
    tp_pips=400,
    max_open_trades=2,
    min_dist_between_orders=105,
    pending_dist_pips=35
)

CONFIG_AGGRESSIVE = BacktestConfig(
    sl_pips=300,
    tp_pips=600,
    max_open_trades=3,
    min_dist_between_orders=50,
    pending_dist_pips=50
)

# Gold-specific constants
GOLD_PIP_SCALE = 0.1  # $0.10 movement = 1 pip
GOLD_TICK_SIZE = 0.10
GOLD_CONTRACT_SIZE = 100  # ounces per standard contract

# Time constants
TRADING_DAYS_PER_YEAR = 252
HOURS_PER_DAY = 24
