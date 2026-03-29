"""
Core module for backtesting engine.
Contains the main backtesting logic and data models.
"""

from .models import Trade, PendingOrder
from .engine import GoldPipEngine

__all__ = ['Trade', 'PendingOrder', 'GoldPipEngine']
