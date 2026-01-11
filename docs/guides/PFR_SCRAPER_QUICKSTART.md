# PFR Scraper - Quick Reference

## ⚡ Quick Commands

```bash
# Test the scraper (30 seconds)
python src/scripts/integrate_pfr_data.py --test

# Enrich workbook with team stats (30 seconds)
python src/scripts/integrate_pfr_data.py --season 2025

# Full integration with game logs (3-5 minutes)
python src/scripts/integrate_pfr_data.py --season 2025 --game-logs

# Custom output path
python src/scripts/integrate_pfr_data.py --season 2025 --output data/enriched.xlsx
```

## 📊 What Gets Scraped

### Team Statistics (29 columns per team)
- Offensive: points, yards, plays, turnovers, passing, rushing
- Expected Points Total (EPA-based metric)
- Score percentage, turnover percentage  
- Yards per play, first downs

### Output Files
- **Test mode**: `outputs/pfr_test_team_stats.csv`
- **Integration**: `data/nfl_2025_model_data_with_moneylines_pfr.xlsx`
  - Sheet: `games` (enriched with ~100 new PFR columns)
  - Sheet: `pfr_team_stats` (raw PFR data)
  - Sheet: `pfr_game_scores` (all games with box score links)
  - Sheet: `pfr_game_logs` (if --game-logs used)

## 🎯 New Columns in Games Sheet

For each stat (e.g., `offense_points`):
```
pfr_home_offense_points    # Home team's season total
pfr_away_offense_points    # Away team's season total
pfr_diff_offense_points    # Differential (home - away)
```

## 🔒 Rate Limiting

- **Max**: 10 requests per minute
- **Auto-throttling**: Yes
- **Min interval**: 6 seconds between requests
- **You'll see**: "Rate limit approached. Sleeping..." messages

## 🐍 Python Usage

```python
from src.utils.pfr_scraper import PFRScraper

scraper = PFRScraper()

# Get team stats
stats = scraper.get_team_stats(2025)

# Get game scores  
games = scraper.get_game_scores(2025, week=1)

# Get team game log
log = scraper.get_team_game_log('NWE', 2025)
```

## 🚀 Integration Workflow

```python
from src.scripts.integrate_pfr_data import PFRIntegrator

# Create integrator
integrator = PFRIntegrator('data/nfl_2025_model_data_with_moneylines.xlsx')

# Run full integration
enriched = integrator.enrich_workbook_with_pfr_stats(
    season=2025,
    scrape_game_logs=False,  # Set True for detailed logs
    output_path='data/enriched.xlsx'
)
```

## 📈 Model Integration

### Add PFR features to model_v3.py

1. **Load enriched workbook**:
   ```python
   games = pd.read_excel('data/nfl_2025_model_data_with_moneylines_pfr.xlsx', sheet_name='games')
   ```

2. **Select top features**:
   ```python
   pfr_features = [
       'pfr_diff_offense_points',
       'pfr_diff_offense_total_yards',
       'pfr_diff_offense_yds_per_play_offense',
       'pfr_diff_offense_turnovers',
       'pfr_diff_offense_pass_td',
       'pfr_diff_offense_rush_yds',
       # ... add more based on correlation analysis
   ]
   ```

3. **Add to X_cols in build_features()**:
   ```python
   # In model_v3.py, build_features method
   feature_cols = delta_features + market_cols + neutral_col + pfr_features
   ```

## 🔍 Feature Analysis

```python
# Check correlation with outcomes
import pandas as pd

games = pd.read_excel('data/nfl_2025_model_data_with_moneylines_pfr.xlsx', sheet_name='games')

# Get PFR differential columns
pfr_diffs = [col for col in games.columns if col.startswith('pfr_diff_')]

# Correlation with margin
correlations = games[pfr_diffs + ['margin_home']].corr()['margin_home'].sort_values(ascending=False)
print(correlations.head(20))

# Top predictive features
print("\nTop 10 PFR features for predicting margin:")
for i, (feat, corr) in enumerate(correlations.head(11).items(), 1):
    if feat != 'margin_home':
        print(f"{i}. {feat}: {corr:.3f}")
```

## ⚠️ Troubleshooting

### No data retrieved
```bash
# Check if you can access PFR
curl https://www.pro-football-reference.com/years/2025/
```

### Import errors
```bash
# Install dependencies
pip install beautifulsoup4 lxml html5lib requests
```

### Slow performance
- This is normal! Rate limiting = 6+ seconds per request
- Use `--test` mode first to verify functionality
- Full game logs take 3-5 minutes (32 teams)

## 📝 File Locations

```
src/utils/pfr_scraper.py              # Core scraper
src/scripts/integrate_pfr_data.py     # Integration tool
src/utils/PFR_SCRAPER_README.md       # Full documentation
reports/PFR_SCRAPER_IMPLEMENTATION.md # Implementation summary
outputs/pfr_test_team_stats.csv       # Test output
```

## ✅ Status Check

After running, verify:
```python
import pandas as pd

# Load enriched workbook
games = pd.read_excel('data/nfl_2025_model_data_with_moneylines_pfr.xlsx', sheet_name='games')

# Count PFR columns
pfr_cols = [col for col in games.columns if 'pfr_' in col]
print(f"✓ Added {len(pfr_cols)} PFR columns")
print(f"✓ Total columns: {len(games.columns)}")
print(f"✓ Total games: {len(games)}")

# Check sample
print("\nSample PFR columns:")
print(games[pfr_cols[:5]].head())
```

## 🎯 Next Steps

1. ✅ Test scraper
2. ⏳ Run integration on your workbook
3. ⏳ Analyze feature correlations
4. ⏳ Add top features to model_v3
5. ⏳ Compare model performance before/after

---

**Questions?** Check [PFR_SCRAPER_README.md](../src/utils/PFR_SCRAPER_README.md) for details
