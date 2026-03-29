"""
Data module for loading and preprocessing market data.
Supports multiple data sources including yfinance and CSV.
"""

import pandas as pd
import numpy as np
from typing import Optional, Union, List
from pathlib import Path


def load_from_yfinance(symbol: str = "GC=F", 
                       period: str = "2y", 
                       interval: str = "1h") -> pd.DataFrame:
    """
    Load OHLCV data from Yahoo Finance.
    
    Args:
        symbol: Trading symbol (default: GC=F for Gold futures)
        period: Data period (e.g., '1d', '5d', '1mo', '2y')
        interval: Candle interval (e.g., '1m', '5m', '1h', '1d')
    
    Returns:
        DataFrame with OHLCV data indexed by datetime
    
    Raises:
        ImportError: If yfinance is not installed
        ValueError: If no data is returned
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("yfinance not installed. Run: pip install yfinance")
    
    print(f"Downloading {symbol} data from Yahoo Finance...")
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    
    if df.empty:
        raise ValueError(f"No data returned for {symbol}")
    
    # Handle multi-level columns if present (newer yfinance versions)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Remove rows with all NaN values
    df = df.dropna(how='all')
    
    print(f"Loaded {len(df)} candles from {df.index.min()} to {df.index.max()}")
    return df


def load_from_csv(file_path: Union[str, Path], 
                  datetime_column: str = 'datetime',
                  date_format: Optional[str] = None) -> pd.DataFrame:
    """
    Load OHLCV data from CSV file.
    
    Args:
        file_path: Path to CSV file
        datetime_column: Name of the datetime column
        date_format: Optional date format string for parsing
    
    Returns:
        DataFrame with OHLCV data indexed by datetime
    
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If required columns are missing
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    print(f"Loading data from {file_path}...")
    df = pd.read_csv(file_path)
    
    # Required columns
    required_cols = ['Open', 'High', 'Low', 'Close']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Parse datetime
    if datetime_column in df.columns:
        df[datetime_column] = pd.to_datetime(df[datetime_column], format=date_format)
        df = df.set_index(datetime_column)
    elif 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], format=date_format)
        df = df.set_index('Date')
    else:
        # Try to use index as datetime
        df.index = pd.to_datetime(df.index)
    
    # Sort by datetime
    df = df.sort_index()
    
    print(f"Loaded {len(df)} candles from {df.index.min()} to {df.index.max()}")
    return df


def remove_weekend_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove weekend data (Saturday and Sunday) from DataFrame.
    
    Args:
        df: DataFrame with datetime index
    
    Returns:
        DataFrame with only weekday data
    """
    initial_count = len(df)
    df_filtered = df[df.index.dayofweek < 5]  # Monday=0, Friday=4
    removed_count = initial_count - len(df_filtered)
    
    if removed_count > 0:
        print(f"Removed {removed_count} weekend candles ({removed_count/initial_count*100:.1f}%)")
    
    return df_filtered


def handle_missing_data(df: pd.DataFrame, 
                        method: str = 'forward_fill',
                        max_gap: int = 5) -> pd.DataFrame:
    """
    Handle missing data in OHLCV DataFrame.
    
    Args:
        df: DataFrame with potential missing values
        method: Handling method - 'forward_fill', 'backward_fill', 'drop', 'interpolate'
        max_gap: Maximum number of consecutive NaN values to fill
    
    Returns:
        DataFrame with missing data handled
    
    Raises:
        ValueError: If invalid method is specified
    """
    null_count_before = df.isnull().sum().sum()
    
    if null_count_before == 0:
        print("No missing data found.")
        return df
    
    print(f"Found {null_count_before} missing values before handling.")
    
    if method == 'forward_fill':
        df = df.fillna(method='ffill', limit=max_gap)
    elif method == 'backward_fill':
        df = df.fillna(method='bfill', limit=max_gap)
    elif method == 'drop':
        df = df.dropna()
    elif method == 'interpolate':
        df = df.interpolate(method='linear', limit=max_gap)
    else:
        raise ValueError(f"Invalid method: {method}. Choose from: forward_fill, backward_fill, drop, interpolate")
    
    # Drop any remaining rows with NaN
    df = df.dropna()
    
    null_count_after = df.isnull().sum().sum()
    print(f"Remaining missing values after handling: {null_count_after}")
    
    return df


def validate_ohlcv_data(df: pd.DataFrame) -> bool:
    """
    Validate OHLCV data integrity.
    
    Checks:
        - High >= Low for all candles
        - Open and Close are within High-Low range
        - No negative prices
        - No duplicate indices
    
    Args:
        df: DataFrame to validate
    
    Returns:
        True if valid, raises ValueError otherwise
    
    Raises:
        ValueError: If validation fails
    """
    issues = []
    
    # Check High >= Low
    if (df['High'] < df['Low']).any():
        invalid_count = (df['High'] < df['Low']).sum()
        issues.append(f"{invalid_count} candles have High < Low")
    
    # Check Open within range
    if ((df['Open'] > df['High']) | (df['Open'] < df['Low'])).any():
        invalid_count = ((df['Open'] > df['High']) | (df['Open'] < df['Low'])).sum()
        issues.append(f"{invalid_count} candles have Open outside High-Low range")
    
    # Check Close within range
    if ((df['Close'] > df['High']) | (df['Close'] < df['Low'])).any():
        invalid_count = ((df['Close'] > df['High']) | (df['Close'] < df['Low'])).sum()
        issues.append(f"{invalid_count} candles have Close outside High-Low range")
    
    # Check negative prices
    if (df[['Open', 'High', 'Low', 'Close']] <= 0).any().any():
        issues.append("Negative prices found")
    
    # Check duplicate indices
    if df.index.duplicated().any():
        dup_count = df.index.duplicated().sum()
        issues.append(f"{dup_count} duplicate timestamps found")
    
    if issues:
        error_msg = "Data validation failed:\n" + "\n".join([f"  - {issue}" for issue in issues])
        raise ValueError(error_msg)
    
    print("Data validation passed.")
    return True


def prepare_data(source: str = 'yfinance',
                 symbol: str = "GC=F",
                 csv_path: Optional[str] = None,
                 remove_weekends: bool = True,
                 handle_missing: bool = True,
                 validate: bool = True) -> pd.DataFrame:
    """
    Main function to load and prepare data from various sources.
    
    Args:
        source: Data source - 'yfinance' or 'csv'
        symbol: Trading symbol (for yfinance)
        csv_path: Path to CSV file (for csv source)
        remove_weekends: Whether to remove weekend data
        handle_missing: Whether to handle missing data
        validate: Whether to validate data integrity
    
    Returns:
        Prepared DataFrame ready for backtesting
    
    Raises:
        ValueError: If invalid source or parameters
    """
    # Load data
    if source == 'yfinance':
        df = load_from_yfinance(symbol=symbol)
    elif source == 'csv':
        if not csv_path:
            raise ValueError("csv_path required when source='csv'")
        df = load_from_csv(csv_path)
    else:
        raise ValueError(f"Invalid source: {source}. Choose from: yfinance, csv")
    
    # Remove weekends if requested
    if remove_weekends:
        df = remove_weekend_data(df)
    
    # Handle missing data if requested
    if handle_missing:
        df = handle_missing_data(df)
    
    # Validate data if requested
    if validate:
        validate_ohlcv_data(df)
    
    return df
