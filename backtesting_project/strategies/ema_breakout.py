"""
Breakout Strategy with Session Filter and Dynamic Support/Resistance.

This strategy implements:
1. NO EMA filter - pure price action breakout
2. Trading session filter - only London-NY overlap (13:00-17:00 UTC)
3. One trade per day limit - prevents overtrading
4. Dynamic Support/Resistance detection - based on recent price structure
5. Stop orders placement - above resistance for buys, below support for sells

Key Features:
- Detects swing highs/lows for S/R levels
- Uses fractal-based support/resistance identification
- Places pending orders at S/R zones
- Only trades during high-liquidity sessions
- Maximum one trade per calendar day

Original logic adapted from Colab notebook, refactored for modularity.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, List
from datetime import datetime, time


class EMABreakoutStrategy:
    """
    Breakout Strategy with Session Filter and Dynamic Support/Resistance.
    
    Buy Setup:
        1. Price breaks above identified Resistance level
        2. Breakout occurs during London-NY overlap (13:00-17:00 UTC)
        3. No trade taken yet today (one trade per day rule)
        4. Stop order placed above resistance
    
    Sell Setup:
        1. Price breaks below identified Support level
        2. Breakout occurs during London-NY overlap (13:00-17:00 UTC)
        3. No trade taken yet today (one trade per day rule)
        4. Stop order placed below support
    
    Attributes:
        lookback_period: Period for identifying swing highs/lows (default: 5)
        min_touches: Minimum touches to confirm S/R level (default: 2)
        session_start_hour: Start hour of trading session in UTC (default: 13)
        session_end_hour: End hour of trading session in UTC (default: 17)
    """
    
    def __init__(
        self, 
        lookback_period: int = 5,
        min_touches: int = 2,
        session_start_hour: int = 13,
        session_end_hour: int = 17
    ):
        """
        Initialize the strategy.
        
        Args:
            lookback_period: Number of candles to look back for swing detection
            min_touches: Minimum number of touches to confirm S/R level
            session_start_hour: Trading session start hour (UTC)
            session_end_hour: Trading session end hour (UTC)
        """
        if lookback_period < 2:
            raise ValueError("lookback_period must be at least 2")
        if min_touches < 1:
            raise ValueError("min_touches must be at least 1")
        if not (0 <= session_start_hour < 24 and 0 < session_end_hour <= 24):
            raise ValueError("Session hours must be between 0 and 24")
        if session_start_hour >= session_end_hour:
            raise ValueError("Session start must be before session end")
        
        self.lookback_period = lookback_period
        self.min_touches = min_touches
        self.session_start_hour = session_start_hour
        self.session_end_hour = session_end_hour
        
        self.signals = None
        self.data_with_indicators = None
        self.support_levels = None
        self.resistance_levels = None
        self.daily_trade_count = None
    
    def _detect_swing_highs(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect swing highs (potential resistance points).
        
        A swing high is a candle whose high is higher than N candles before and after.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Series of boolean indicating swing highs
        """
        highs = data['High']
        swing_highs = pd.Series(False, index=data.index)
        
        # Need at least lookback_period candles on each side
        for i in range(self.lookback_period, len(highs) - self.lookback_period):
            current_high = highs.iloc[i]
            
            # Check if current high is highest in the window
            left_window = highs.iloc[i-self.lookback_period:i]
            right_window = highs.iloc[i+1:i+self.lookback_period+1]
            
            if (current_high > left_window.max()) and (current_high >= right_window.max()):
                swing_highs.iloc[i] = True
        
        return swing_highs
    
    def _detect_swing_lows(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect swing lows (potential support points).
        
        A swing low is a candle whose low is lower than N candles before and after.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Series of boolean indicating swing lows
        """
        lows = data['Low']
        swing_lows = pd.Series(False, index=data.index)
        
        # Need at least lookback_period candles on each side
        for i in range(self.lookback_period, len(lows) - self.lookback_period):
            current_low = lows.iloc[i]
            
            # Check if current low is lowest in the window
            left_window = lows.iloc[i-self.lookback_period:i]
            right_window = lows.iloc[i+1:i+self.lookback_period+1]
            
            if (current_low < left_window.min()) and (current_low <= right_window.min()):
                swing_lows.iloc[i] = True
        
        return swing_lows
    
    def _identify_resistance_levels(
        self, 
        data: pd.DataFrame, 
        swing_highs: pd.Series,
        tolerance_pips: float = 5.0
    ) -> pd.DataFrame:
        """
        Identify resistance levels from swing highs.
        
        Groups nearby swing highs into resistance zones.
        
        Args:
            data: DataFrame with OHLCV data
            swing_highs: Boolean series indicating swing highs
            tolerance_pips: Tolerance in pips for grouping levels
            
        Returns:
            DataFrame with columns: level, touches, last_tested, strength
        """
        if swing_highs.sum() == 0:
            return pd.DataFrame(columns=['level', 'touches', 'last_tested', 'strength'])
        
        # Get all swing high prices
        swing_high_prices = data.loc[swing_highs, 'High'].reset_index()
        
        if len(swing_high_prices) == 0:
            return pd.DataFrame(columns=['level', 'touches', 'last_tested', 'strength'])
        
        # Group nearby highs into zones
        tolerance = tolerance_pips * 0.0001  # Convert pips to price
        
        resistance_zones = []
        used_indices = set()
        
        for idx, row in swing_high_prices.iterrows():
            if idx in used_indices:
                continue
            
            current_level = row['High']
            zone_highs = [(idx, current_level)]
            used_indices.add(idx)
            
            # Find other highs in the same zone
            for idx2, row2 in swing_high_prices.iterrows():
                if idx2 in used_indices or idx2 == idx:
                    continue
                
                if abs(row2['High'] - current_level) <= tolerance:
                    zone_highs.append((idx2, row2['High']))
                    used_indices.add(idx2)
            
            # Calculate zone statistics
            if len(zone_highs) >= self.min_touches:
                avg_level = np.mean([h[1] for h in zone_highs])
                last_tested = max([h[0] for h in zone_highs])
                touches = len(zone_highs)
                
                # Strength based on number of touches and recency
                days_since_test = (len(data) - last_tested) / 24  # Assuming hourly data
                recency_factor = max(0, 1 - days_since_test / 10)  # Decay over 10 days
                strength = touches * recency_factor
                
                resistance_zones.append({
                    'level': avg_level,
                    'touches': touches,
                    'last_tested': last_tested,
                    'strength': strength,
                    'highs': [h[0] for h in zone_highs]
                })
        
        if len(resistance_zones) == 0:
            return pd.DataFrame(columns=['level', 'touches', 'last_tested', 'strength'])
        
        # Sort by strength (strongest first)
        df = pd.DataFrame(resistance_zones)
        df = df.sort_values('strength', ascending=False).reset_index(drop=True)
        
        return df[['level', 'touches', 'last_tested', 'strength']]
    
    def _identify_support_levels(
        self, 
        data: pd.DataFrame, 
        swing_lows: pd.Series,
        tolerance_pips: float = 5.0
    ) -> pd.DataFrame:
        """
        Identify support levels from swing lows.
        
        Groups nearby swing lows into support zones.
        
        Args:
            data: DataFrame with OHLCV data
            swing_lows: Boolean series indicating swing lows
            tolerance_pips: Tolerance in pips for grouping levels
            
        Returns:
            DataFrame with columns: level, touches, last_tested, strength
        """
        if swing_lows.sum() == 0:
            return pd.DataFrame(columns=['level', 'touches', 'last_tested', 'strength'])
        
        # Get all swing low prices
        swing_low_prices = data.loc[swing_lows, 'Low'].reset_index()
        
        if len(swing_low_prices) == 0:
            return pd.DataFrame(columns=['level', 'touches', 'last_tested', 'strength'])
        
        # Group nearby lows into zones
        tolerance = tolerance_pips * 0.0001  # Convert pips to price
        
        support_zones = []
        used_indices = set()
        
        for idx, row in swing_low_prices.iterrows():
            if idx in used_indices:
                continue
            
            current_level = row['Low']
            zone_lows = [(idx, current_level)]
            used_indices.add(idx)
            
            # Find other lows in the same zone
            for idx2, row2 in swing_low_prices.iterrows():
                if idx2 in used_indices or idx2 == idx:
                    continue
                
                if abs(row2['Low'] - current_level) <= tolerance:
                    zone_lows.append((idx2, row2['Low']))
                    used_indices.add(idx2)
            
            # Calculate zone statistics
            if len(zone_lows) >= self.min_touches:
                avg_level = np.mean([l[1] for l in zone_lows])
                last_tested = max([l[0] for l in zone_lows])
                touches = len(zone_lows)
                
                # Strength based on number of touches and recency
                days_since_test = (len(data) - last_tested) / 24  # Assuming hourly data
                recency_factor = max(0, 1 - days_since_test / 10)  # Decay over 10 days
                strength = touches * recency_factor
                
                support_zones.append({
                    'level': avg_level,
                    'touches': touches,
                    'last_tested': last_tested,
                    'strength': strength,
                    'lows': [l[0] for l in zone_lows]
                })
        
        if len(support_zones) == 0:
            return pd.DataFrame(columns=['level', 'touches', 'last_tested', 'strength'])
        
        # Sort by strength (strongest first)
        df = pd.DataFrame(support_zones)
        df = df.sort_values('strength', ascending=False).reset_index(drop=True)
        
        return df[['level', 'touches', 'last_tested', 'strength']]
    
    def _is_in_session(self, timestamp: pd.Timestamp) -> bool:
        """
        Check if timestamp is within trading session.
        
        Args:
            timestamp: Datetime to check
            
        Returns:
            True if within session, False otherwise
        """
        hour = timestamp.hour
        
        # Handle session that might cross midnight
        if self.session_start_hour < self.session_end_hour:
            return self.session_start_hour <= hour < self.session_end_hour
        else:
            # Session crosses midnight (e.g., 22:00 - 02:00)
            return hour >= self.session_start_hour or hour < self.session_end_hour
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all required indicators and identify S/R levels.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with added indicator columns
        """
        df = data.copy()
        
        # Detect swing points
        df['swing_high'] = self._detect_swing_highs(df)
        df['swing_low'] = self._detect_swing_lows(df)
        
        # Identify S/R levels (using entire dataset up to each point)
        # For real-time simulation, we'd use rolling windows
        self.swing_highs = df['swing_high']
        self.swing_lows = df['swing_low']
        
        # Identify support and resistance zones
        self.resistance_levels = self._identify_resistance_levels(df, self.swing_highs)
        self.support_levels = self._identify_support_levels(df, self.swing_lows)
        
        # Add session filter column
        df['in_session'] = df.index.map(self._is_in_session)
        
        # Track daily trades
        df['date'] = df.index.date
        self.daily_trade_count = {}
        
        self.data_with_indicators = df
        return df
    
    def _get_nearest_resistance(self, current_price: float, num_levels: int = 3) -> Optional[float]:
        """
        Get nearest resistance level above current price.
        
        Args:
            current_price: Current market price
            num_levels: Number of top resistance levels to consider
            
        Returns:
            Nearest resistance level or None
        """
        if self.resistance_levels is None or len(self.resistance_levels) == 0:
            return None
        
        # Filter resistances above current price
        above_resistances = self.resistance_levels[
            self.resistance_levels['level'] > current_price
        ].head(num_levels)
        
        if len(above_resistances) == 0:
            return None
        
        # Return the nearest one (lowest level above price)
        return above_resistances['level'].min()
    
    def _get_nearest_support(self, current_price: float, num_levels: int = 3) -> Optional[float]:
        """
        Get nearest support level below current price.
        
        Args:
            current_price: Current market price
            num_levels: Number of top support levels to consider
            
        Returns:
            Nearest support level or None
        """
        if self.support_levels is None or len(self.support_levels) == 0:
            return None
        
        # Filter supports below current price
        below_supports = self.support_levels[
            self.support_levels['level'] < current_price
        ].head(num_levels)
        
        if len(below_supports) == 0:
            return None
        
        # Return the nearest one (highest level below price)
        return below_supports['level'].max()
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals based on the strategy logic.
        
        Args:
            data: DataFrame with OHLCV data (will calculate indicators if not present)
        
        Returns:
            Series of signals: 1=Buy, -1=Sell, 0=No signal
        """
        # Calculate indicators if not already done
        if 'in_session' not in data.columns:
            df = self.calculate_indicators(data)
        else:
            df = data.copy()
        
        # Initialize signals
        signals = pd.Series(0, index=df.index)
        
        # Track trades per day
        daily_trades = {}
        
        # Parameters for breakout confirmation
        breakout_threshold = 0.0001  # 1 pip breakout confirmation
        
        print(f"\n=== Signal Generation ===")
        print(f"Lookback period: {self.lookback_period}")
        print(f"Trading session: {self.session_start_hour:02d}:00 - {self.session_end_hour:02d}:00 UTC")
        print(f"Identified {len(self.resistance_levels)} resistance levels")
        print(f"Identified {len(self.support_levels)} support levels")
        
        buy_signals = 0
        sell_signals = 0
        
        for i in range(1, len(df)):
            current_time = df.index[i]
            current_date = current_time.date()
            current_price = df['Close'].iloc[i]
            current_high = df['High'].iloc[i]
            current_low = df['Low'].iloc[i]
            
            # Check if in trading session
            if not df['in_session'].iloc[i]:
                continue
            
            # Check daily trade limit
            if current_date not in daily_trades:
                daily_trades[current_date] = 0
            
            if daily_trades[current_date] >= 1:
                continue  # Already traded today
            
            # Get nearest S/R levels
            nearest_resistance = self._get_nearest_resistance(current_price)
            nearest_support = self._get_nearest_support(current_price)
            
            # Check for resistance breakout (BUY signal)
            if nearest_resistance is not None:
                # Price breaking above resistance
                if current_high > (nearest_resistance + breakout_threshold):
                    # Confirm close above resistance
                    if current_price > nearest_resistance:
                        signals.iloc[i] = 1
                        daily_trades[current_date] += 1
                        buy_signals += 1
            
            # Check for support breakdown (SELL signal) - only if no buy signal
            if signals.iloc[i] == 0 and nearest_support is not None:
                # Price breaking below support
                if current_low < (nearest_support - breakout_threshold):
                    # Confirm close below support
                    if current_price < nearest_support:
                        signals.iloc[i] = -1
                        daily_trades[current_date] += 1
                        sell_signals += 1
        
        self.signals = signals
        self.daily_trade_count = daily_trades
        
        total_signals = buy_signals + sell_signals
        
        print(f"\nTotal candles analyzed: {len(df)}")
        print(f"Candles in session: {df['in_session'].sum()}")
        print(f"Buy signals: {buy_signals}")
        print(f"Sell signals: {sell_signals}")
        print(f"Total signals: {total_signals}")
        print(f"Days with trades: {len(daily_trades)}")
        
        return signals
    
    def get_signal_details(self, index: int) -> dict:
        """
        Get detailed information about signals at a specific index.
        
        Args:
            index: Row index in the DataFrame
        
        Returns:
            Dictionary with signal details
        """
        if self.data_with_indicators is None or self.signals is None:
            raise RuntimeError("Must call generate_signals() first")
        
        if index < 1 or index >= len(self.data_with_indicators):
            raise IndexError(f"Index {index} out of range")
        
        df = self.data_with_indicators
        row = df.iloc[index]
        signal = self.signals.iloc[index]
        
        # Get relevant S/R levels
        current_price = row['Close']
        nearest_resistance = self._get_nearest_resistance(current_price)
        nearest_support = self._get_nearest_support(current_price)
        
        return {
            'datetime': df.index[index],
            'signal': signal,
            'signal_type': 'BUY' if signal == 1 else ('SELL' if signal == -1 else 'NONE'),
            'open': row['Open'],
            'high': row['High'],
            'low': row['Low'],
            'close': row['Close'],
            'in_session': row['in_session'],
            'nearest_resistance': nearest_resistance,
            'nearest_support': nearest_support,
            'distance_to_resistance': (nearest_resistance - current_price) * 10000 if nearest_resistance else None,
            'distance_to_support': (current_price - nearest_support) * 10000 if nearest_support else None
        }
    
    def analyze_setups(self) -> dict:
        """
        Analyze the frequency and characteristics of setups.
        
        Returns:
            Dictionary with setup analysis statistics
        """
        if self.data_with_indicators is None or self.signals is None:
            raise RuntimeError("Must call generate_signals() first")
        
        df = self.data_with_indicators
        
        # Count swing points
        total_swing_highs = self.swing_highs.sum()
        total_swing_lows = self.swing_lows.sum()
        
        # Count session hours
        session_candles = df['in_session'].sum()
        
        # Signal counts
        buy_signals = (self.signals == 1).sum()
        sell_signals = (self.signals == -1).sum()
        
        # Daily trade distribution
        if self.daily_trade_count:
            days_with_1_trade = sum(1 for count in self.daily_trade_count.values() if count == 1)
            avg_trades_per_day = sum(self.daily_trade_count.values()) / len(self.daily_trade_count) if self.daily_trade_count else 0
        else:
            days_with_1_trade = 0
            avg_trades_per_day = 0
        
        # S/R level statistics
        avg_resistance_touches = self.resistance_levels['touches'].mean() if len(self.resistance_levels) > 0 else 0
        avg_support_touches = self.support_levels['touches'].mean() if len(self.support_levels) > 0 else 0
        
        return {
            'total_candles': len(df),
            'session_candles': session_candles,
            'swing_points': {
                'total_swing_highs': total_swing_highs,
                'total_swing_lows': total_swing_lows
            },
            'support_resistance': {
                'resistance_levels_identified': len(self.resistance_levels),
                'support_levels_identified': len(self.support_levels),
                'avg_resistance_touches': avg_resistance_touches,
                'avg_support_touches': avg_support_touches
            },
            'signals': {
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'total_signals': buy_signals + sell_signals
            },
            'daily_trading': {
                'days_with_trades': len(self.daily_trade_count) if self.daily_trade_count else 0,
                'days_with_1_trade': days_with_1_trade,
                'avg_trades_per_trading_day': avg_trades_per_day
            }
        }
    
    def get_sr_levels_summary(self) -> dict:
        """
        Get summary of identified Support and Resistance levels.
        
        Returns:
            Dictionary with S/R level details
        """
        if self.resistance_levels is None or self.support_levels is None:
            raise RuntimeError("Must call calculate_indicators() first")
        
        return {
            'resistance_levels': self.resistance_levels.to_dict('records') if len(self.resistance_levels) > 0 else [],
            'support_levels': self.support_levels.to_dict('records') if len(self.support_levels) > 0 else []
        }
