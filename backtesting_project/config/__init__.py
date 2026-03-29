"""
Configuration module initialization.
"""

from .settings import (
    BacktestConfig,
    CONFIG_CONSERVATIVE,
    CONFIG_MODERATE,
    CONFIG_AGGRESSIVE,
    GOLD_PIP_SCALE,
    GOLD_TICK_SIZE,
    GOLD_CONTRACT_SIZE
)

__all__ = [
    'BacktestConfig',
    'CONFIG_CONSERVATIVE',
    'CONFIG_MODERATE',
    'CONFIG_AGGRESSIVE',
    'GOLD_PIP_SCALE',
    'GOLD_TICK_SIZE',
    'GOLD_CONTRACT_SIZE'
]
