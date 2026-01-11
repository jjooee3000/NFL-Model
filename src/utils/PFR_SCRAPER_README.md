# Pro Football Reference Web Scraper

Comprehensive web scraping system for Pro-Football-Reference.com data to enhance NFL prediction model.

## Features

### Automated Data Collection
- **Team Statistics**: Season-level offensive and defensive stats for all 32 teams
- **Game Scores**: Complete game results with box score links
- **Game Logs**: Detailed game-by-game performance for each team
- **Advanced Stats**: Passing, rushing, receiving, and defensive analytics

### Rate Limiting & Ethics
- **10 requests per minute maximum** - respects site limits
- **Automatic throttling** - built-in delays between requests
- **Polite user agent** - identifies as research bot
- **Error handling** - graceful failures with logging

## Data Available

### Team Stats (Season Level)
```
- Points For/Against
- Total Yards Offense/Defense  
- Yards per Play
- Turnovers Lost/Forced
- Pass Completions/Attempts/Yards/TDs/INTs
- Rush Attempts/Yards/TDs
- First Downs
- Penalties/Penalty Yards
- Time of Possession
- Third Down Conversions
- Red Zone Efficiency
```

### Game-by-Game Logs
```
- Weekly performance stats
- Opponent information
- Game location (home/away/neutral)
- Result (W/L)
- Points scored/allowed
- Individual game statistics
```

### Advanced Metrics
```
- Expected Points Added (EPA)
- Success Rate
- Air Yards
- Yards After Catch
- Pressure Rate
- Completion % Over Expectation
```

## Quick Start

### Test the Scraper
```bash
# Test scraping (fetches team stats only)
python src/scripts/integrate_pfr_data.py --test

# Output: outputs/pfr_test_team_stats.csv
```

### Basic Integration
```bash
# Enrich workbook with PFR team statistics
python src/scripts/integrate_pfr_data.py --season 2025

# Creates: data/nfl_2025_model_data_with_moneylines_pfr.xlsx
```

### Full Integration (Slow)
```bash
# Include detailed game logs (~3-5 minutes due to rate limiting)
python src/scripts/integrate_pfr_data.py --season 2025 --game-logs

# This will:
# 1. Scrape team stats (1 request)
# 2. Scrape game scores (1 request)  
# 3. Scrape 32 team game logs (32 requests = ~3 minutes)
```

### Custom Output
```bash
# Specify output path
python src/scripts/integrate_pfr_data.py --season 2025 --output data/enriched_workbook.xlsx
```

## Python API Usage

### Quick Team Stats
```python
from src.utils.pfr_scraper import PFRScraper

scraper = PFRScraper()

# Get 2025 season team statistics
team_stats = scraper.get_team_stats(season=2025)

print(f"Found {len(team_stats)} teams")
print(team_stats.head())
```

### Game Scores
```python
# Get all games from 2025 season
all_games = scraper.get_game_scores(season=2025)

# Get specific week
week_1_games = scraper.get_game_scores(season=2025, week=1)
```

### Team Game Logs
```python
# Get New England Patriots game-by-game stats
nwe_log = scraper.get_team_game_log('NWE', season=2025)

print(f"Patriots played {len(nwe_log)} games")
```

### Comprehensive Scrape
```python
# Scrape everything and save to files
data = scraper.scrape_season_data(
    season=2025,
    output_dir='data/pfr_scraped'
)

# Returns dict with:
# - team_stats
# - game_scores
# - passing (advanced)
# - rushing (advanced)
# - receiving (advanced)
# - defense (advanced)
# - team_game_logs
```

## Data Integration

The `integrate_pfr_data.py` script automatically:

1. **Loads** your existing workbook
2. **Scrapes** current season data from PFR
3. **Merges** stats into games dataframe
4. **Creates differential features** (home - away for each stat)
5. **Saves** enriched workbook with new sheets

### New Columns Added

For each team statistic (e.g., `points_for`), creates:
- `pfr_home_points_for` - Home team's points scored
- `pfr_away_points_for` - Away team's points scored  
- `pfr_diff_points_for` - Differential (home - away)

This gives the model access to ~100+ new features!

### New Sheets Created

- `pfr_team_stats` - Raw team statistics from PFR
- `pfr_game_scores` - All game results with box score links
- `pfr_game_logs` - Game-by-game logs (if --game-logs flag used)

## Rate Limiting Details

### Why Rate Limiting Matters
Sports-Reference.com flags users making too many requests. We respect their servers by:

1. **Max 10 requests per minute** - hard limit
2. **Minimum 6 seconds between requests** - prevents bursts
3. **Automatic backoff** - waits when approaching limit
4. **Request tracking** - monitors requests in rolling 60-second window

### Estimated Times

| Operation | Requests | Time |
|-----------|----------|------|
| Team stats | 1 | ~6 seconds |
| Game scores | 1 | ~6 seconds |
| Advanced stats (4 types) | 4 | ~24 seconds |
| Team game logs (32 teams) | 32 | ~3-4 minutes |
| Full season scrape | ~38 | ~4-5 minutes |

## Model Enhancement Ideas

### New Features from PFR Data

1. **Seasonal Strength Metrics**
   ```python
   # Offensive efficiency differential
   pfr_diff_yards_per_play
   pfr_diff_third_down_pct
   pfr_diff_red_zone_td_pct
   ```

2. **Defensive Prowess**
   ```python
   # Defensive differential
   pfr_diff_defense_yards_per_play
   pfr_diff_defense_sacks
   pfr_diff_defense_turnovers
   ```

3. **Special Teams**
   ```python
   pfr_diff_punt_return_avg
   pfr_diff_kick_return_avg
   pfr_diff_field_goal_pct
   ```

4. **Advanced Analytics**
   ```python
   pfr_diff_epa_per_play
   pfr_diff_success_rate
   pfr_diff_explosive_play_rate
   ```

### Integration with Existing Model

The PFR data complements your current features:

| Current Feature | PFR Enhancement |
|-----------------|-----------------|
| Momentum metrics (EMA, trends) | Season-long aggregates |
| Recent performance (8-game window) | Full season context |
| Market data (spreads, totals) | Underlying team quality |
| Weather data | Outdoor game performance splits |

## Troubleshooting

### "Rate limit approached" warning
This is normal! The scraper is protecting you from being flagged. It will wait automatically.

### "No data retrieved"
- Check internet connection
- Verify season year is valid (PFR has data from 1920+)
- Site may be down or blocking requests

### Slow performance
- Full game log scraping takes 3-5 minutes (32 teams × 6 seconds)
- This is intentional to respect rate limits
- Use `--test` mode first to verify it works

### Missing stats
- Some advanced stats require Stathead subscription
- Basic team/game stats are always free
- Injury reports may be subscription-only

## Future Enhancements

### Potential Additions
- [ ] Player-level statistics aggregation
- [ ] Historical data backfill (prior seasons)
- [ ] Play-by-play data (drive efficiency, red zone)
- [ ] Weather integration from PFR stadium info
- [ ] Vegas line movement tracking
- [ ] Coaching/roster changes impact

### Advanced Scraping
- [ ] Box score details (quarter-by-quarter)
- [ ] Situational splits (3rd down, red zone, etc.)
- [ ] Opponent-adjusted statistics
- [ ] Strength of schedule calculations

## Legal & Ethical Notes

✅ **Allowed**:
- Scraping publicly available data for personal research
- Respecting rate limits
- Proper attribution to Pro-Football-Reference.com

❌ **Not Allowed**:
- Commercial use without permission
- Circumventing paywalls
- Ignoring rate limits
- Redistributing scraped data

**Data Source**: Data provided by [Pro-Football-Reference.com](https://www.pro-football-reference.com)

## Support

For questions about the scraper:
1. Check logs for error messages
2. Test with `--test` flag first
3. Verify you can access PFR in a browser
4. Check if your IP has been temporarily rate-limited

## Examples

### Example 1: Quick Stats Check
```python
from src.utils.pfr_scraper import quick_team_stats

stats = quick_team_stats(season=2025)
print(stats[['team', 'offense_points', 'defense_points']].head(10))
```

### Example 2: Weekly Integration
```python
from src.scripts.integrate_pfr_data import PFRIntegrator

integrator = PFRIntegrator('data/nfl_2025_model_data_with_moneylines.xlsx')
integrator.load_workbook()

# Scrape latest stats
team_stats = integrator.scrape_team_stats(2025)

# Enrich and save
enriched = integrator.enrich_workbook_with_pfr_stats(
    season=2025,
    output_path='data/weekly_update.xlsx'
)
```

### Example 3: Historical Backfill
```python
from src.utils.pfr_scraper import PFRScraper

scraper = PFRScraper()

# Scrape multiple seasons
for year in range(2020, 2026):
    print(f"Scraping {year}...")
    scraper.scrape_season_data(
        season=year,
        output_dir=f'data/pfr_historical/{year}'
    )
    print(f"✓ Completed {year}\n")
```

## Citation

When using this data in research or analysis:

```
Data Source: Pro-Football-Reference.com
URL: https://www.pro-football-reference.com
Accessed: [Date]
```
