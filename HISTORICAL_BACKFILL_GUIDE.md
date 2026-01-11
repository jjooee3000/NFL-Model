# Historical Data Backfill Guide

## Overview
This guide covers scraping 5 years of NFL data (2020-2024) from Pro-Football-Reference and integrating it with your 2025 model data.

## What Gets Scraped

### Complete Data Extraction (No Shortcuts)
For each season (2020-2024), the script extracts:

1. **Team Statistics (Offense)** - 32 teams × ~29 columns
   - Points scored, yards gained, turnovers, etc.

2. **Team Defense Statistics** - 32 teams × ~29 columns  
   - Points allowed, yards allowed, opponent turnovers, etc.

3. **Game Schedule & Results** - ~280 games per season
   - Scores, dates, locations, overtime info

4. **Team Game Logs** - ALL 32 teams × 17-20 games each
   - Game-by-game performance for every team
   - ~560 rows per season

5. **Advanced Statistics** - 4 categories
   - Advanced Passing (EPA, air yards, pressure rate)
   - Advanced Rushing (yards before/after contact, broken tackles)
   - Advanced Receiving (target share, YAC over expected)
   - Advanced Defense (tackles for loss, QB hits, coverage)

6. **Situational Statistics** - 3 categories
   - Conversions (3rd/4th down efficiency)
   - Drives (drive statistics and efficiency)
   - Scoring (red zone, goal-to-go breakdown)

### Total Data Points
- **5 years × 40 requests/year = 200 total requests**
- **Estimated time: 20 minutes** (with 6-second intervals for rate limiting)
- **~1,400 games across all seasons**
- **160 team-seasons of data**

## Usage

### Step 1: Run Complete Backfill
```powershell
python src/scripts/backfill_historical_data.py --integrate
```

This will:
1. Scrape ALL data types for 2020-2024 (20 minutes)
2. Save individual CSV files per year
3. Automatically integrate into main workbook
4. Create backup with historical data merged

**Output:**
- `data/pfr_historical/2020_team_stats.csv` (and similar for 2021-2024)
- `data/pfr_historical/2020_team_defense.csv`
- `data/pfr_historical/2020_games.csv`
- `data/pfr_historical/2020_team_gamelogs.csv` (all 32 teams)
- `data/pfr_historical/2020_advanced_passing.csv`
- `data/pfr_historical/2020_advanced_rushing.csv`
- `data/pfr_historical/2020_advanced_receiving.csv`
- `data/pfr_historical/2020_advanced_defense.csv`
- `data/pfr_historical/2020_situational_conversions.csv`
- `data/pfr_historical/2020_situational_drives.csv`
- `data/pfr_historical/2020_situational_scoring.csv`
- `data/nfl_model_data_historical_integrated.xlsx` (main workbook with 2020-2025 data)

### Step 2: Verify Integration
```powershell
python -c "import pandas as pd; df = pd.read_excel('data/nfl_model_data_historical_integrated.xlsx', sheet_name='games'); print(f'Total games: {len(df)}'); print(f'Years: {sorted(df[\"season\"].unique())}')"
```

Expected output:
```
Total games: ~1,677 (277 from 2025 + 1,400 from 2020-2024)
Years: [2020, 2021, 2022, 2023, 2024, 2025]
```

## Advanced Options

### Resume Capability
The script automatically saves progress after each year. If interrupted:
```powershell
python src/scripts/backfill_historical_data.py --integrate
```
It will skip already-completed years and continue from where it left off.

### Custom Year Range
```powershell
# Just 2023-2024
python src/scripts/backfill_historical_data.py --start-year 2023 --end-year 2024 --integrate

# Just 2020
python src/scripts/backfill_historical_data.py --start-year 2020 --end-year 2020
```

### Specific Data Types Only
```powershell
# Only team stats and games (faster)
python src/scripts/backfill_historical_data.py --data-types team_stats games

# Everything except game logs (saves time on 32×5 = 160 requests)
python src/scripts/backfill_historical_data.py --data-types team_stats team_defense games advanced_stats situational_stats
```

### Integration Only (After Manual Scraping)
```powershell
# If you already scraped but want to re-integrate
python src/scripts/backfill_historical_data.py --integrate-only
```

### Consolidation Only (Create Excel from CSVs)
```powershell
# Create consolidated workbook from existing CSVs
python src/scripts/backfill_historical_data.py --consolidate-only
```

## Rate Limiting

The scraper automatically enforces:
- **Maximum 10 requests per minute** (PFR requirement)
- **Minimum 6 seconds between requests**
- Automatic backoff if approaching limit

**Do not run multiple instances simultaneously** - this will violate rate limits and potentially get IP blocked.

## Output Structure

### Individual Year Files
```
data/pfr_historical/
├── 2020_team_stats.csv
├── 2020_team_defense.csv
├── 2020_games.csv
├── 2020_team_gamelogs.csv
├── 2020_advanced_passing.csv
├── 2020_advanced_rushing.csv
├── 2020_advanced_receiving.csv
├── 2020_advanced_defense.csv
├── 2020_situational_conversions.csv
├── 2020_situational_drives.csv
├── 2020_situational_scoring.csv
├── 2020_data.json
├── [same for 2021-2024]
└── backfill_progress.json
```

### Integrated Workbook
```
data/nfl_model_data_historical_integrated.xlsx
├── games (2020-2025 merged)
├── injuries_qb (from original)
├── passing (from original)
├── [all original sheets preserved]
├── pfr_team_stats_historical (2020-2024 team offense)
├── pfr_advanced_passing (2020-2024)
├── pfr_advanced_rushing (2020-2024)
├── pfr_advanced_receiving (2020-2024)
├── pfr_advanced_defense (2020-2024)
└── [situational stats sheets]
```

## Next Steps After Backfill

1. **Update model training script** to use integrated workbook:
   ```python
   data = pd.read_excel('data/nfl_model_data_historical_integrated.xlsx', sheet_name='games')
   # Now you have 5+ years of training data instead of just 2025
   ```

2. **Add historical features** to model:
   - Year-over-year team performance trends
   - Multi-season aggregates
   - Historical head-to-head records

3. **Re-train models** with expanded dataset:
   ```powershell
   python src/models/model_v3.py  # Will use more training data
   ```

4. **Compare performance**: Models trained on 5 years vs 1 year

## Troubleshooting

### "No historical game files found"
Run the scraping first:
```powershell
python src/scripts/backfill_historical_data.py
```

### Rate limit errors
Wait 1 minute, then resume. Progress is saved automatically.

### "FileNotFoundError: main workbook"
Check that `data/nfl_2025_model_data_with_moneylines.xlsx` exists, or specify path:
```powershell
python src/scripts/backfill_historical_data.py --main-workbook "path/to/your/workbook.xlsx" --integrate
```

### Unicode errors on Windows
The script uses UTF-8 file encoding. If you see codec errors, they're logged but won't stop execution.

## Data Quality Notes

- **Game logs**: All 32 teams × 17-20 games per season = complete coverage
- **Advanced stats**: Aggregated from player-level data (comprehensive)
- **Situational stats**: Red zone, conversions, drives (full detail)
- **No sampling or shortcuts**: Every data point extracted

## Time Estimates

| Data Type | Requests/Year | Time/Year |
|-----------|---------------|-----------|
| Team Stats | 1 | 6 sec |
| Team Defense | 1 | 6 sec |
| Games | 1 | 6 sec |
| Game Logs (32 teams) | 32 | 3.2 min |
| Advanced Stats (4 types) | 4 | 24 sec |
| Situational Stats | 1 | 6 sec |
| **Total per year** | **40** | **~4 min** |
| **5 years** | **200** | **~20 min** |

*Note: Actual time may vary based on network speed and PFR server response times.*
