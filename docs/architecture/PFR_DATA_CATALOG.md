# Pro Football Reference - Data Source Catalog

## Overview
This document catalogs all available data sources on Pro-Football-Reference.com for historical NFL data extraction (2020-2025).

## URL Patterns & Data Sources

### 1. Season-Level Team Statistics

**URL Pattern**: `/years/{year}/`

**Available Tables**:
- `AFC` - AFC standings (W/L, division, points)
- `NFC` - NFC standings (W/L, division, points)
- `team_stats` - Team offensive statistics (28 columns)
  - Points, yards, plays, turnovers
  - Passing: completions, attempts, yards, TDs, INTs
  - Rushing: attempts, yards, TDs
  - First downs, penalties
  - Expected Points Total
- `passing` - Team passing stats (25 columns)
- `rushing` - Team rushing stats (11 columns)
- `kicking` - Kicking statistics (25 columns)
- `punting` - Punting statistics (15 columns)
- `returns` - Return statistics (14 columns)
- `team_scoring` - Scoring breakdown (21 columns)
- `team_conversions` - 3rd/4th down conversions (12 columns)
- `drives` - Drive statistics (12 columns)

**Years Available**: 2020-2025 (6 seasons)
**Status**: ✅ Already implemented

---

### 2. Team Defensive Statistics

**URL Pattern**: `/years/{year}/opp.htm`

**Available Tables**:
- `team_stats` - Opponent/defensive statistics
  - Points allowed
  - Yards allowed
  - Turnovers forced
  - Sacks, tackles
  - Pass defense
  - Rush defense

**Years Available**: 2020-2025
**Status**: 🔄 Needs implementation

---

### 3. Game Schedule & Results

**URL Pattern**: `/years/{year}/games.htm`

**Available Tables**:
- `games` - All games for the season
  - Week, date, time
  - Teams, scores
  - Location (home/away/neutral)
  - Box score links

**Weekly**: `/years/{year}/week_{week}.htm`

**Years Available**: 2020-2025
**Status**: ✅ Already implemented

---

### 4. Advanced Passing Statistics

**URL Pattern**: `/years/{year}/passing_advanced.htm`

**Available Metrics**:
- Expected Points Added (EPA)
- Completion % over expectation
- Air yards
- Yards after catch
- Drop rate
- Bad throw %
- Pressure rate
- Time to throw

**Years Available**: 2020-2025
**Status**: 🔄 Needs implementation

---

### 5. Advanced Rushing Statistics

**URL Pattern**: `/years/{year}/rushing_advanced.htm`

**Available Metrics**:
- Yards before/after contact
- Broken tackles
- Rush EPA
- Success rate
- Stuff rate

**Years Available**: 2020-2025
**Status**: 🔄 Needs implementation

---

### 6. Advanced Receiving Statistics

**URL Pattern**: `/years/{year}/receiving_advanced.htm`

**Available Metrics**:
- Target share
- Catch rate
- Yards per route run
- Drop rate
- Contested catches
- YAC over expected

**Years Available**: 2020-2025
**Status**: 🔄 Needs implementation

---

### 7. Advanced Defensive Statistics

**URL Pattern**: `/years/{year}/defense_advanced.htm`

**Available Metrics**:
- Tackles for loss
- QB hits, hurries
- Pass breakups
- Missed tackle rate
- Coverage stats

**Years Available**: 2020-2025
**Status**: 🔄 Needs implementation

---

### 8. Team Game Logs

**URL Pattern**: `/teams/{team}/{year}.htm`

**Available Data**:
- Game-by-game performance
- Offensive stats per game
- Defensive stats per game
- Home/away splits
- Opponent information

**Teams**: All 32 NFL teams
**Years Available**: 2020-2025
**Status**: ✅ Already implemented

---

### 9. Special Situations

**Red Zone Scoring**: `/years/{year}/redzone-scoring.htm`
- Red zone attempts, TDs, FGs
- Red zone efficiency

**Penalties**: `/years/{year}/penalties.htm`
- Penalty counts by type
- Penalty yards
- Most penalized teams

**Third Down Conversions**: Included in `team_conversions`

**Years Available**: 2020-2025
**Status**: 🔄 Needs implementation

---

### 10. Player Statistics

**Passing**: `/years/{year}/passing.htm`
**Rushing**: `/years/{year}/rushing.htm`
**Receiving**: `/years/{year}/receiving.htm`
**Defense**: `/years/{year}/defense.htm`

**Note**: Player stats require aggregation to team level

**Years Available**: 2020-2025
**Status**: ⏸️ Future enhancement

---

## Data Extraction Priority

### Phase 1: Essential (Week 1)
1. ✅ Team offensive stats (already done)
2. 🔄 Team defensive stats
3. ✅ Game schedules (already done)
4. ✅ Team game logs (already done)

### Phase 2: Advanced Analytics (Week 2)
1. 🔄 Advanced passing stats
2. 🔄 Advanced rushing stats
3. 🔄 Advanced receiving stats
4. 🔄 Advanced defensive stats

### Phase 3: Situational (Week 3)
1. 🔄 Red zone efficiency
2. 🔄 Third/fourth down conversions
3. 🔄 Drive statistics
4. 🔄 Penalty statistics

### Phase 4: Historical Backfill (Week 4)
1. 🔄 2020 season data
2. 🔄 2021 season data
3. 🔄 2022 season data
4. 🔄 2023 season data
5. 🔄 2024 season data

---

## Historical Data Plan

### Years to Backfill: 2020-2024 (5 seasons)

**Estimated Data Points**:
- 5 years × 32 teams = 160 team-seasons
- 5 years × ~272 games/season = ~1,360 games
- Multiple stat categories per team/game

**Estimated Time**:
- Basic stats: ~10 requests/year = 50 requests = 5 minutes
- Advanced stats: ~20 requests/year = 100 requests = 10 minutes
- Team game logs: 32 teams × 5 years = 160 requests = 16 minutes
- **Total**: ~30-40 minutes with rate limiting

**Storage**:
- JSON files by year: `data/pfr_historical/2020.json`
- CSV exports: `data/pfr_historical/2020_team_stats.csv`
- Consolidated workbook: Add historical sheets

---

## Implementation Roadmap

### Step 1: Enhanced Scraper (Today)
```python
# Add methods to PFRScraper class
- get_team_defense_stats(year)
- get_advanced_passing_stats(year)
- get_advanced_rushing_stats(year)
- get_advanced_receiving_stats(year)
- get_advanced_defense_stats(year)
- get_redzone_stats(year)
- get_penalty_stats(year)
```

### Step 2: Historical Backfill Script (Today)
```python
# Create backfill script
def backfill_historical_data(start_year=2020, end_year=2024):
    for year in range(start_year, end_year + 1):
        # Scrape all data sources for year
        # Save to year-specific files
        # Progress tracking
```

### Step 3: Workbook Integration (Tomorrow)
```python
# Merge historical data into model workbook
# Create historical performance features
# Add year-over-year comparisons
```

### Step 4: Model Enhancement (Next Week)
```python
# Add historical features to model_v3
# Test with 5 years of data
# Evaluate improvement
```

---

## Data Source Details

### Team Stats Table Columns (28 total)
```
- team: Team abbreviation
- g: Games played
- points: Points scored
- total_yards: Total offensive yards
- plays_offense: Total plays
- yds_per_play_offense: Yards per play
- turnovers: Turnovers lost
- fumbles_lost: Fumbles lost
- first_down: First downs
- pass_cmp: Pass completions
- pass_att: Pass attempts
- pass_yds: Passing yards
- pass_td: Passing touchdowns
- pass_int: Interceptions thrown
- pass_net_yds_per_att: Net yards per pass attempt
- pass_fd: First downs passing
- rush_att: Rush attempts
- rush_yds: Rushing yards
- rush_td: Rushing touchdowns
- rush_yds_per_att: Yards per rush
- rush_fd: First downs rushing
- penalties: Penalties
- penalties_yds: Penalty yards
- pen_fd: First downs via penalty
- score_pct: Scoring percentage
- turnover_pct: Turnover percentage
- exp_pts_tot: Expected points total
- ranker: Season rank
```

### Games Table Columns
```
- week_num: Week number
- game_day_of_week: Day of week
- game_date: Date
- boxscore_word: Box score link
- winner: Winning team
- loser: Losing team
- pts_win: Winning points
- pts_lose: Losing points
- location: H/A/@
- game_duration: Duration
- over_under: Over/under result
```

---

## Rate Limiting Strategy

**PFR Rate Limits**: 10 requests per minute

**Backfill Plan**:
1. Scrape 1 year at a time
2. Save progress after each year
3. Resume capability if interrupted
4. Batch requests: team stats + games + advanced stats
5. Minimum 6 seconds between requests

**Total Estimated Time for 5-Year Backfill**:
- Season stats: 5 requests × 6 sec = 30 seconds
- Defensive stats: 5 requests × 6 sec = 30 seconds  
- Game schedules: 5 requests × 6 sec = 30 seconds
- Advanced stats (4 types): 20 requests × 6 sec = 2 minutes
- Team game logs (sample 10 teams): 50 requests × 6 sec = 5 minutes
- **Total**: ~8-10 minutes for comprehensive backfill

---

## Next Actions

1. **Index Completion** ✅
   - Catalog all available tables
   - Document column structures
   - Identify priorities

2. **Scraper Enhancement** (Next)
   - Add defensive stats method
   - Add advanced stats methods
   - Add situational stats methods

3. **Historical Backfill** (Today)
   - Create backfill script
   - Run for 2020-2024
   - Validate data quality

4. **Integration** (Tomorrow)
   - Merge into workbook
   - Create historical features
   - Test model with expanded data

---

## Questions to Consider

1. **Which stats are most predictive?**
   - Prioritize high-value data
   - Skip low-signal metrics

2. **How far back to go?**
   - 5 years = good balance
   - More = diminishing returns
   - League rules/teams change

3. **Player vs Team aggregation?**
   - Team-level easier, faster
   - Player-level more granular
   - Start with team, add player later

4. **Storage format?**
   - JSON for raw data
   - CSV for tabular exports
   - Excel sheets for model integration
   - All three?

---

**Status**: Catalog complete, ready for implementation
**Next**: Run enhanced scraper to extract all identified data sources
