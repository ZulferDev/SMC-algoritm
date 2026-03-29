# Backtesting Project Structure

Proyek ini adalah hasil refactoring dari kode backtesting strategy algo trading yang awalnya dibuat di Google Colab.

## Struktur Folder

```
backtesting_project/
├── core/               # Engine utama backtesting
│   ├── __init__.py
│   ├── engine.py       # GoldPipEngine - logic utama backtest
│   └── models.py       # Data class untuk Trade dan PendingOrder
├── strategies/         # Definisi strategi trading
│   ├── __init__.py
│   └── ema_breakout.py # Strategi EMA + Price Action Breakout
├── data/               # Manajemen data dan loader
│   ├── __init__.py
│   ├── loader.py       # Fungsi load data dari berbagai sumber
│   └── preprocessing.py# Preprocessing dan cleaning data
├── utils/              # Fungsi-fungsi helper
│   ├── __init__.py
│   ├── metrics.py      # Perhitungan metrics (win rate, drawdown, dll)
│   └── visualization.py# Plotting dan visualisasi
├── config/             # Konfigurasi parameter
│   ├── __init__.py
│   └── settings.py     # Parameter default (SL, TP, pip_scale, dll)
├── reports/            # Output laporan dan analisis
│   └── .gitkeep
├── main.py             # Entry point untuk menjalankan backtest
├── requirements.txt    # Dependencies
└── README.md           # Dokumentasi ini
```

## Cara Menjalankan

```bash
# Install dependencies
pip install -r requirements.txt

# Jalankan backtest
python main.py
```

## Perubahan dari Kode Asli

1. **Modularisasi**: Kode dipisah menjadi modul-modul terpisah berdasarkan fungsi
2. **Penghapusan Code Colab-specific**: Menghapus `!pip install` dan perintah Colab lainnya
3. **Perbaikan Bug**: Memperbaiki beberapa kesalahan fatal yang ditemukan
4. **Type Hinting**: Menambahkan type hints untuk better code quality
5. **Logging**: Menambahkan logging untuk debugging

## Kekurangan dan Bug yang Ditemukan di Kode Asli

### Fatal Errors:
1. **Duplicate yfinance download**: Data didownload 2 kali dengan variabel berbeda (`df_1h` dan `df`)
2. **Inconsistent data source**: Menggunakan Kaggle dataset di awal, lalu override dengan yfinance
3. **Missing null handling**: Tidak ada handling untuk data kosong setelah shift() operations
4. **Hardcoded parameters**: SL/TP dan parameter lain hardcoded di main script

### Issues:
1. **No validation**: Tidak ada validasi untuk input data
2. **Magic numbers**: Banyak angka hardcoded tanpa penjelasan
3. **No error handling**: Tidak ada try-except blocks
4. **Mixed concerns**: Logic backtest tercampur dengan data loading dan visualization

## Next Steps

- [ ] Implementasi proper logging
- [ ] Tambah unit tests
- [ ] Implementasi multiple strategies support
- [ ] Tambah parameter optimization dengan Optuna
- [ ] Export results ke CSV/Excel
