"""
Data models for trading operations.
Defines Trade and PendingOrder dataclasses.
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class Trade:
    """
    Represents a single trade position.
    
    Attributes:
        entry_time: Timestamp when the trade was entered
        entry_price: Price at which the trade was entered
        type: 'BUY' or 'SELL'
        sl_price: Stop loss price level
        tp_price: Take profit price level
        sl_pips: Stop loss in pips
        tp_pips: Take profit in pips
        exit_time: Timestamp when the trade was closed (filled after exit)
        exit_price: Price at which the trade was closed (filled after exit)
        pips_gained: Profit/loss in pips (filled after exit)
        status: Trade status - 'OPEN', 'SL_HIT', 'TP_HIT'
    """
    entry_time: pd.Timestamp
    entry_price: float
    type: str  # 'BUY' or 'SELL'
    sl_price: float
    tp_price: float
    sl_pips: float
    tp_pips: float
    
    # Will be filled upon exit
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pips_gained: float = 0.0
    status: str = 'OPEN'
    
    def to_dict(self) -> dict:
        """Convert trade to dictionary format."""
        return {
            'entry_time': self.entry_time,
            'entry_price': self.entry_price,
            'type': self.type,
            'sl_price': self.sl_price,
            'tp_price': self.tp_price,
            'sl_pips': self.sl_pips,
            'tp_pips': self.tp_pips,
            'exit_time': self.exit_time,
            'exit_price': self.exit_price,
            'pips_gained': self.pips_gained,
            'status': self.status
        }


@dataclass
class PendingOrder:
    """
    Represents a pending order waiting to be triggered.
    
    Attributes:
        create_time: Timestamp when the pending order was created
        type: Order type - 'BUY_STOP', 'BUY_LIMIT', 'SELL_STOP', 'SELL_LIMIT'
        price: Trigger price for the pending order
        sl_pips: Stop loss in pips (will be applied when order triggers)
        tp_pips: Take profit in pips (will be applied when order triggers)
    """
    create_time: pd.Timestamp
    type: str
    price: float
    sl_pips: float
    tp_pips: float
    
    def is_buy(self) -> bool:
        """Check if this is a buy order."""
        return 'BUY' in self.type
    
    def is_sell(self) -> bool:
        """Check if this is a sell order."""
        return 'SELL' in self.type
    
    def is_stop(self) -> bool:
        """Check if this is a stop order."""
        return 'STOP' in self.type
    
    def is_limit(self) -> bool:
        """Check if this is a limit order."""
        return 'LIMIT' in self.type
