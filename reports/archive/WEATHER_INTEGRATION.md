# Weather Integration Guide

## Overview

Weather data has been integrated into the NFL prediction model to capture environmental factors that impact game outcomes. This implementation uses the Open-Meteo Historical Weather API to backfill historical weather conditions at kickoff time for each game.

## Components

### 1. Weather API Client (`src/utils/weather.py`)
- Fetches historical weather from Open-Meteo reanalysis datasets (ERA5)
- Free for non-commercial use, no API key required
- Returns: temperature, humidity, precipitation, wind speed/gusts, pressure, cloud cover
- Handles hourly precision with optional time-window averaging

### 2. Stadium Coordinates Database (`src/utils/stadiums.py`)
- Maps all 32 NFL team codes to home stadium lat/lon
- Includes dome/retractable flags for weather relevance filtering
- Coordinates verified for 2024-2025 season stadiums

### 3. Backfill Script (`src/scripts/backfill_weather.py`)
- Batch-fetches weather for all games in the workbook
- Parses game datetime from `game_date (YYYY-MM-DD)` and `kickoff_time_local` columns
- Adds weather columns to games sheet: `temp_f`, `wind_mph`, `wind_gust_mph`, `precip_inch`, `humidity_pct`, `pressure_hpa`, `cloud_pct`, `is_indoor`
- Rate-limited (default 0.3s delay between requests)

### 4. Model Integration (`src/models/model_v3.py`)
- Weather features added to candidate feature list
- Creates rolling/momentum features for weather variables same as other stats
- Automatically merges weather data from games sheet during training

## Usage

### Backfill Weather Data

```bash
# Dry run (test without saving)
python src/scripts/backfill_weather.py --dry-run --limit 10

# Full backfill (saves to workbook)
python src/scripts/backfill_weather.py

# Custom delay for rate limiting
python src/scripts/backfill_weather.py --delay 0.5
```

### Train Model with Weather

No changes needed—v3 automatically includes weather features if present in the workbook:

```bash
python src/scripts/record_predictions.py --train-week 14 --variant tuned --use-best-params
```

## Weather Features

Features added to team-level data (when available):
- `temp_f`: Temperature in Fahrenheit at kickoff
- `wind_mph`: Wind speed in mph
- `wind_gust_mph`: Wind gusts in mph
- `precip_inch`: Precipitation amount
- `humidity_pct`: Relative humidity percentage
- `pressure_hpa`: Atmospheric pressure
- `cloud_pct`: Cloud cover percentage
- `is_indoor`: Binary flag for dome/retractable stadiums

These generate momentum features:
- Rolling averages (e.g., `temp_f_pre8`)
- Exponential moving averages (e.g., `temp_f_ema8`)
- Trends, volatility, season averages, recent ratios

And delta features:
- Home vs away weather deltas for each momentum type

## Expected Impact

Weather should improve prediction accuracy for:
- **Totals**: Cold/wind → lower scoring; precipitation → lower scoring
- **Spreads**: Passing teams disadvantaged in high wind; dome teams on road in bad weather
- **Pass-heavy offenses**: More sensitive to wind/precip than run-heavy teams

Initial tests will quantify the improvement via the comparison harness.

## Data Quality Notes

- Open-Meteo uses reanalysis models (9-25km grid) rather than point observations
- Accuracy is good for general conditions but may miss hyper-local effects
- Dome games (`is_indoor=1`) have weather data but it's not relevant to gameplay
- Future: could add retractable roof status (open/closed) for more precision

## Maintenance

- Stadium coordinates updated annually if teams relocate
- API is free for <10,000 req/day; backfill of full season fits well within limits
- Weather data is static once backfilled (historical reanalysis doesn't change)

## Next Steps

1. ✓ Backfill weather for all games
2. Train v3 with weather features and compare to non-weather baseline
3. Add weather interaction terms (e.g., wind × pass rate, temp × dome flag)
4. Calibrate feature importance to verify weather signal
5. Document improvements in comparison report
