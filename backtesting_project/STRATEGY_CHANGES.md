# Perubahan Strategi Breakout dengan Session Filter & Dynamic Support/Resistance

## 📋 Ringkasan Perubahan

Saya telah melakukan **refactoring total** pada strategi `EMABreakoutStrategy` sesuai permintaan Anda:

### ✅ Perubahan yang Dilakukan

#### 1. **Menghilangkan EMA Filter** ❌
- **Sebelum**: Menggunakan EMA 10-period sebagai filter trend
- **Sekarang**: Pure price action breakout tanpa EMA
- **Alasan**: Fokus pada level S/R yang lebih objektif

#### 2. **Menambahkan Session Filter (London-NY Overlap)** ⏰
- **Jam Trading**: 13:00 - 17:00 UTC
- **Alasan**: 
  - Likuiditas tertinggi saat London dan New York overlap
  - Spread paling ketat
  - Volatilitas optimal untuk breakout
  - Menghindari false breakout di session Asia yang sepi

#### 3. **One Trade Per Day Limit** 📅
- **Rule**: Maksimal 1 trade per hari kalender
- **Implementasi**: Tracking harian menggunakan dictionary
- **Alasan**: 
  - Mencegah overtrading
  - Fokus pada setup terbaik saja
  - Mengurangi exposure risk

#### 4. **Dynamic Support/Resistance Detection** 🎯
Ini adalah **fitur utama** yang dikembangkan:

##### Algoritma Deteksi S/R:
```python
1. Deteksi Swing Highs/Lows menggunakan fractal pattern
   - Swing High: High tertinggi dalam N candle sebelum dan sesudah
   - Swing Low: Low terendah dalam N candle sebelum dan sesudah

2. Grouping level terdekat menjadi zone
   - Tolerance: 5 pips untuk grouping
   - Minimum touches: 2 kali sentuh untuk konfirmasi

3. Scoring strength setiap level
   - Faktor jumlah touches (semakin banyak semakin kuat)
   - Faktor recency (semakin baru semakin kuat)
   - Strength = touches × recency_factor
```

##### Parameter yang Dapat Disesuaikan:
- `lookback_period`: Jumlah candle untuk swing detection (default: 5)
- `min_touches`: Minimum sentuhan untuk konfirmasi S/R (default: 2)
- `tolerance_pips`: Toleransi grouping level (default: 5 pips)

#### 5. **Logic Breakout yang Disesuaikan** 📈

**BUY Setup:**
```
1. Price break ABOVE resistance level terdekati
2. Breakout terjadi dalam session 13:00-17:00 UTC
3. Belum ada trade hari ini
4. Entry: Buy stop order di atas resistance
```

**SELL Setup:**
```
1. Price break BELOW support level terdekat
2. Breakout terjadi dalam session 13:00-17:00 UTC
3. Belum ada trade hari ini
4. Entry: Sell stop order di bawah support
```

**Breakout Confirmation:**
- Threshold: 1 pip di luar level S/R
- Close confirmation: Candle harus close di luar level

---

## 🆚 Perbandingan: Kode Lama vs Baru

| Aspek | Kode Lama (EMA) | Kode Baru (S/R) |
|-------|-----------------|-----------------|
| **Filter** | EMA 10-period | Session time (13-17 UTC) |
| **Entry Trigger** | 2-candle pattern + EMA | Breakout S/R level |
| **Max Trades/Hari** | Unlimited | 1 trade/hari |
| **Support/Resistance** | Tidak ada | Dynamic fractal-based |
| **Kompleksitas** | Simple | Moderate-Advanced |
| **Objectivity** | Subjektif (EMA choice) | Objektif (price action) |

---

## 📊 Struktur Data Support/Resistance

Setiap level S/R memiliki atribut:

```python
{
    'level': 2034.56,        # Price level
    'touches': 3,            # Jumlah kali disentuh
    'last_tested': 145,      # Index candle terakhir
    'strength': 2.85         # Score strength (touches × recency)
}
```

**Strength Calculation:**
```python
days_since_test = (total_candles - last_tested) / 24  # Asumsi hourly data
recency_factor = max(0, 1 - days_since_test / 10)     # Decay 10 hari
strength = touches × recency_factor
```

---

## 🔧 Cara Menggunakan

### Basic Usage
```python
from strategies import EMABreakoutStrategy

# Default parameters
strategy = EMABreakoutStrategy()

# Custom parameters
strategy = EMABreakoutStrategy(
    lookback_period=5,      # Swing detection window
    min_touches=2,          # Minimum touches for confirmation
    session_start_hour=13,  # London-NY overlap start
    session_end_hour=17     # London-NY overlap end
)

# Generate signals
signals = strategy.generate_signals(data)

# Get S/R levels summary
sr_levels = strategy.get_sr_levels_summary()
print(f"Resistance levels: {len(sr_levels['resistance_levels'])}")
print(f"Support levels: {len(sr_levels['support_levels'])}")
```

### Running Backtest
```bash
cd /workspace/backtesting_project
python main.py
```

### Custom Configuration
```python
from main import run_backtest
from config import CONFIG_MODERATE

# Aggressive: More sensitive S/R detection
metrics, trades, monthly = run_backtest(
    config=CONFIG_MODERATE,
    lookback_period=3,      # More swings detected
    min_touches=1,          # Less strict confirmation
    session_start=8,        # Wider session
    session_end=20
)

# Conservative: Strict S/R detection
metrics, trades, monthly = run_backtest(
    config=CONFIG_MODERATE,
    lookback_period=10,     # Fewer but stronger swings
    min_touches=3,          # More touches required
    session_start=13,       # Only peak liquidity
    session_end=16
)
```

---

## 📈 Output Analysis

### Setup Analysis Report
```
=== Signal Generation ===
Lookback period: 5
Trading session: 13:00 - 17:00 UTC
Identified 12 resistance levels
Identified 15 support levels

Total candles analyzed: 17520
Candles in session: 2920
Buy signals: 45
Sell signals: 38
Total signals: 83
Days with trades: 83

Top 3 Resistance Levels:
  1. Price: 2045.3200 | Touches: 5 | Strength: 4.75
  2. Price: 2038.7500 | Touches: 4 | Strength: 3.92
  3. Price: 2052.1800 | Touches: 3 | Strength: 2.85

Top 3 Support Levels:
  1. Price: 2015.4500 | Touches: 6 | Strength: 5.40
  2. Price: 2022.8900 | Touches: 4 | Strength: 3.68
  3. Price: 2008.3200 | Touches: 3 | Strength: 2.91
```

---

## ⚠️ Catatan Penting

### 1. **Data Requirement**
- Strategy ini membutuhkan **hourly data** atau higher timeframe
- Untuk tick data, perlu agregasi ke OHLC terlebih dahulu
- Timezone harus UTC untuk session filter bekerja dengan benar

### 2. **Lookback Period Trade-off**
- **Kecil (3-5)**: Lebih banyak sinyal, lebih banyak false breakout
- **Besar (10-20)**: Lebih sedikit sinyal, lebih reliable tapi lagging

### 3. **Min Touches Trade-off**
- **Kecil (1-2)**: Lebih banyak level S/R, termasuk yang lemah
- **Besar (3-5)**: Hanya level kuat yang terdeteksi, mungkin miss opportunity

### 4. **Session Filter**
- Default 13-17 UTC optimal untuk **EURUSD, GBPUSD, XAUUSD**
- Untuk pair lain, sesuaikan session:
  - **JPY pairs**: Tambah Tokyo session (00:00-08:00 UTC)
  - **AUD pairs**: Tambah Sydney session (22:00-06:00 UTC)

---

## 🐛 Potensi Issues & Solusi

### Issue 1: Tidak Ada S/R Level Terdeteksi
**Penyebab**: 
- Data terlalu sedikit (< 100 candle)
- `min_touches` terlalu tinggi
- Market sedang ranging tight

**Solusi**:
```python
strategy = EMABreakoutStrategy(
    lookback_period=3,  # Kurangi dari 5
    min_touches=1       # Kurangi dari 2
)
```

### Issue 2: Terlalu Banyak False Breakout
**Penyebab**:
- `lookback_period` terlalu kecil
- `tolerance_pips` terlalu ketat

**Solusi**:
```python
strategy = EMABreakoutStrategy(
    lookback_period=10,  # Besarkan dari 5
    min_touches=3        # Besarkan dari 2
)
```

### Issue 3: Tidak Ada Trade Sama Sekali
**Penyebab**:
- Session filter terlalu sempit
- S/R level terlalu jauh dari current price

**Solusi**:
```python
strategy = EMABreakoutStrategy(
    session_start_hour=8,   # Mulai dari London open
    session_end_hour=20,    # Sampai NY close
    lookback_period=3       # Lebih sensitif
)
```

---

## 🚀 Rekomendasi Pengembangan Selanjutnya

### 1. **Rolling Window S/R**
Saat ini S/R dihitung menggunakan seluruh data historis. Untuk live trading:
```python
# Gunakan rolling window 100 candle terakhir
self.resistance_levels = self._identify_resistance_levels(
    df.iloc[max(0, i-100):i],  # Only recent data
    swing_highs.iloc[max(0, i-100):i]
)
```

### 2. **Multi-Timeframe Confirmation**
Tambahkan konfirmasi dari higher timeframe:
```python
# Check jika breakout juga terjadi di daily chart
daily_breakout = self._check_daily_breakout(current_price, resistance)
if daily_breakout:
    strength_multiplier = 1.5
```

### 3. **Volume Confirmation**
Tambahkan filter volume untuk validasi breakout:
```python
avg_volume = df['Volume'].rolling(20).mean()
if current_volume > avg_volume * 1.5:
    # Breakout dengan volume tinggi = lebih reliable
    signal_strength = 'STRONG'
```

### 4. **Dynamic SL/TP Based on S/R**
Sesuaikan SL/TP berdasarkan jarak ke S/R berikutnya:
```python
# Untuk BUY: TP di resistance berikutnya
next_resistance = self._get_next_resistance(entry_price)
tp_pips = (next_resistance - entry_price) * 10000

# Untuk SELL: TP di support berikutnya
next_support = self._get_next_support(entry_price)
tp_pips = (entry_price - next_support) * 10000
```

---

## 📚 Referensi

1. **Fractal Support/Resistance**: Bill Williams' Fractal Indicator
2. **Session Trading**: London-NY overlap volatility patterns
3. **Breakout Trading**: Thomas Bulkowski's Encyclopedia of Chart Patterns

---

## ✅ Testing Checklist

- [x] Import strategy tanpa error
- [x] Deteksi swing highs/lows berfungsi
- [x] Grouping S/R zones berfungsi
- [x] Session filter (13-17 UTC) aktif
- [x] One trade per day limit enforced
- [x] Breakout logic dengan threshold 1 pip
- [x] Signal generation menghasilkan output
- [x] Main.py updated dengan parameter baru

---

**Dibuat**: 2024
**Last Updated**: Sekarang
**Version**: 2.0 (S/R Breakout Strategy)
