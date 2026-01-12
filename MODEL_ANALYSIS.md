# NFL Model Comprehensive Analysis
**Generated**: 2026-01-11  
**Purpose**: Identify model improvement opportunities before HOU@PIT prediction

---

## Executive Summary

### Critical Findings
1. **🚨 WEATHER DATA GAP**: Model expects 7 weather features but all are **0% populated** for 2020+ games
2. **🚨 REST DAYS GAP**: Model expects home/away rest days but **0% populated**
3. **✅ ODDS INTEGRATION**: Already configured (276 historical games in odds table)
4. **💡 UNTAPPED DATA**: 3,048 PFR gamelogs + 544 team stats rows per table NOT being used by primary model

### Quick Wins (Immediate Impact)
- **Backfill weather data** (0% → ~80% for outdoor games)
- **Calculate rest days** from schedule (simple date math)
- **Leverage PFR team stats** already in database (offensive/defensive efficiency)

---

## 1. Current Model Architecture

### Model: NFLHybridModelV3
- **Algorithm**: RandomForest (default), Ridge, or XGBoost
- **Training Window**: Default 8 games rolling average
- **Feature Engineering**:
  - Rolling averages (N-game windows)
  - Momentum features (EMA, trend, volatility, season avg, recent ratio)
  - Phase 1 interactions (pressure differential, turnover impact, efficiency products)
  - Phase 2 opponent adjustments (placeholder - not fully implemented)

### Data Sources Used
```python
# From model_v3.py load_workbook()
- games table (SQLite) → 2,331 rows, 50 columns
- team_games table → 546 rows, 56 columns  
- odds table → 276 rows with spread/total/moneylines
```

### Features Expected (from _candidate_features)
**Base Features** (~40 total):
```
Performance Metrics:
- points_for, points_against
- turnovers_give, turnovers_take
- penalties, penalty_yards

Offensive:
- yards_per_play, total_yards, plays
- pass_yds, rush_yds
- rush_td, rush_ypa
- third_down_pct, fourth_down_pct

Defensive:
- yards_per_play_allowed, plays_allowed
- sacks_made, sacks_allowed
- hurries_made, hurries_allowed
- blitzes_sent, blitzes_faced

Special Teams:
- punts, punt_yards_per_punt

Passing Advanced:
- dadot (depth of target)
- air_yards, yac_yards
- qb_knockdowns_made/allowed
- pressures_made/allowed
- pass_bats

WEATHER (CRITICAL GAP):
- temp_f
- wind_mph
- wind_gust_mph
- precip_inch
- humidity_pct
- pressure_hpa
- is_indoor

REST:
- home_rest_days (GAP)
- away_rest_days (GAP)
```

**Momentum Features** (created from base features):
- `{feature}_pre{window}` - Rolling N-game average
- `{feature}_ema{window}` - Exponential moving average
- `{feature}_trend{window}` - Linear slope (momentum direction)
- `{feature}_vol{window}` - Coefficient of variation (consistency)
- `{feature}_season_avg` - Season-to-date average
- `{feature}_recent_ratio` - Recent performance vs season average (hot/cold indicator)

**Phase 1 Interactions** (16 new features):
```
1. total_pressure_made/allowed (sacks + hurries)
2. pressure_advantage (made - allowed)
3. pressure_ratio (relative strength)
4. offensive_effectiveness (yards_per_play × plays)
5. defensive_effectiveness (yards_allowed × plays)
6. turnover_differential (takeaways - giveaways)
7. turnover_impact (differential × efficiency)
8. points_per_play_offense/defense (efficiency)
9. rushing_potency (rush_td × ypa)
10. third_down_conversions (pct × attempts)
11. offensive/defensive_consistency (inverse volatility)
12. blitz_effectiveness/vulnerability
13. punt_effectiveness
14. offensive/defensive_form (EMA vs season avg)
15. tempo_efficiency (pace × yards_per_play)
```

**Market Features** (from odds table):
```
- close_spread_home
- close_total
- open_spread_home, open_total
- imp_p_home_novig (implied probability)
- spread_move_home (line movement)
- total_move (total movement)
```

**Total Features**: ~300-350 features (40 base × 6 momentum types + 16 phase1 + 7 market + 7 weather)

---

## 2. Data Quality Assessment

### Table: `games` (2,331 rows)

| Feature Category | Columns | Populated | Status |
|-----------------|---------|-----------|--------|
| **Weather** | 7 (temp, wind, precip, humidity, pressure, indoor, cloud) | **0%** | 🚨 CRITICAL GAP |
| **Rest Days** | 2 (home_rest_days, away_rest_days) | **0%** | 🚨 CRITICAL GAP |
| **Venue** | 7 (stadium, city, state, country, surface, capacity, roof_type) | ~85% | ✅ Good |
| **Scores** | 4 (home_score, away_score, overtime, point_differential) | 100% | ✅ Complete |
| **Odds (ESPN)** | 15 (NEW Phase 1 columns) | ~1% (3 games) | ⏳ In Progress |
| **Game Info** | 6 (game_id, date, week, teams) | 100% | ✅ Complete |

### Table: `team_games` (546 rows)
**Purpose**: Per-team per-game statistics (base features)

| Feature Group | Example Columns | Status |
|--------------|----------------|--------|
| Scoring | points_for, points_against | ✅ Populated |
| Turnovers | turnovers_give, turnovers_take | ✅ Populated |
| Offensive | yards, plays, yards_per_play, pass_yds, rush_yds | ✅ Populated |
| Defensive | sacks_made/allowed, hurries, blitzes | ✅ Populated |
| Penalties | penalties, penalty_yards | ✅ Populated |
| Conversions | third_down_pct, fourth_down_pct | ✅ Populated |

**Issue**: Only 546 rows vs 2,331 games = 546 team-game records (273 games × 2 teams)
- Missing: 2,058 games worth of team_games data
- **This is a MAJOR gap** - model can only use ~12% of available games!

### Table: `odds` (276 rows)
✅ **Already integrated** into model (line 100 model_v3.py)
- Covers 276 games (~12% of total)
- Has: spread, total, moneylines (open/close)
- Model uses: spread/total movement as features

### Tables: PFR Data (UNTAPPED)

| Table | Rows | Columns | Usage in Model |
|-------|------|---------|----------------|
| **pfr_team_gamelogs** | 3,048 | ? | ❌ NOT USED by model_v3 |
| **pfr_team_stats** | 160 | ? | ✅ Used by model_v4 only |
| **pfr_team_defense** | ? | ? | ✅ Used by model_v4 only |
| **pfr_advanced_defense** | 4,989 | 30 | ❌ NOT USED |
| **pfr_advanced_passing** | 553 | 43 | ❌ NOT USED |
| **pfr_advanced_receiving** | 2,687 | 24 | ❌ NOT USED |
| **pfr_advanced_rushing** | 1,869 | 18 | ❌ NOT USED |

**Opportunity**: 3,048 PFR gamelogs contain rich historical data not being used by primary prediction model

### Tables: Team Stats (544 rows each)

| Table | Key Metrics | Usage |
|-------|------------|-------|
| **offense_team_games** | yards_per_play, plays, turnovers, time_of_possession | ✅ Used (partially) |
| **defense_team_games** | blitzes_sent, hurries_made, pressures, def_dadot | ✅ Used (partially) |
| **defense_drives_team_games** | opp_3d_pct, opp_4d_pct, first_downs_allowed | ✅ Used (partially) |
| **penalties_team_games** | penalties, penalty_yards (both teams) | ✅ Used |
| **odds_team_games** | close_spread_team, vs_line, ou_result | ❌ NOT USED |
| **passing** | completion%, pass_yds, TD, INT, sacks, QB rating | ❌ NOT USED |

---

## 3. Data Gaps & Opportunities

### 🚨 CRITICAL GAPS (Immediate Fix Required)

#### Gap 1: Weather Data (0% populated)
**Model Expectation**: 7 weather features (temp, wind, precip, humidity, pressure, indoor, cloud)  
**Current Reality**: All weather columns are NULL/0 for games since 2020  
**Impact**: Model treats all games as identical weather conditions (major accuracy loss)

**Fix**:
```python
# Script already exists: backfill_weather.py (referenced in model code)
# Solution: Use NOAA API or weather service to backfill historical weather
# Target: ~80% coverage (outdoor games only, exclude domes)
# Estimated improvement: -0.5 to -1.0 pts MAE (weather accounts for ~3-4 pts in extreme conditions)
```

#### Gap 2: Rest Days (0% populated)
**Model Expectation**: home_rest_days, away_rest_days  
**Current Reality**: Both columns empty  
**Impact**: Can't account for short rest (Thu night games), bye weeks, playoff rest advantage

**Fix**:
```python
# Calculate from game_date column using simple date arithmetic
# For each team: days_since_last_game = current_game_date - previous_game_date
# Estimated improvement: -0.2 to -0.3 pts MAE (short rest = -2.5 pts on average)
```

#### Gap 3: team_games Coverage (12% of games)
**Expected**: 2,331 games × 2 teams = 4,662 team_game records  
**Actual**: 546 team_game records (273 games)  
**Missing**: 88% of game data!

**Impact**: Model can only train on 273 games instead of 2,331 games
- Severely limits training data
- Can't leverage 2020-2024 historical games
- Only using 2025 season data effectively

**Fix**:
```python
# Option 1: Populate team_games from PFR gamelogs (3,048 rows available)
# Option 2: Merge team_games data from other stat tables (offense/defense/penalties)
# Option 3: Extract team-level stats from games table if available
# Estimated improvement: -1.0 to -2.0 pts MAE (10x more training data)
```

### 💡 IMPROVEMENT OPPORTUNITIES

#### Opportunity 1: Leverage PFR Team Stats
**Available**: 160 rows (32 teams × 5 seasons) in pfr_team_stats  
**Contains**: Season-long averages for offense/defense efficiency  
**Current Usage**: Only used by model_v4, NOT by production model_v3

**Potential Features**:
```
- Offensive efficiency (yards/play, points/drive, TD%)
- Defensive efficiency (yards/play allowed, points/drive allowed)
- Turnover differential season avg
- Red zone efficiency
- Third down conversion % (season baseline)
```

**Implementation**: Create season-level baseline features to complement game-level rolling features

#### Opportunity 2: Use PFR Gamelogs (3,048 rows)
**Available**: Game-by-game results for 2020-2024  
**Contains**: 
- pts_off, pts_def (actual scores)
- yards_off, pass_yds_off, rush_yds_off
- to_off, to_def (turnovers)
- exp_pts_off, exp_pts_def, exp_pts_st (expected points - highly predictive!)

**Current Usage**: ❌ NOT USED at all

**Potential Value**:
- **Expected Points**: EPA (Expected Points Added) is one of the most predictive modern metrics
- Backfill team_games table with this data (covers 3,048 team-game records vs current 546)
- Add special teams impact (exp_pts_st)

#### Opportunity 3: Integrate Advanced PFR Stats
**Available**: 
- pfr_advanced_defense (4,989 rows): completion% allowed, yards/target, blitzes, QB pressures
- pfr_advanced_passing (553 rows): air yards, YAC, batted passes, throwaways, drops
- pfr_advanced_receiving (2,687 rows): ADOT, broken tackles, drops, YAC
- pfr_advanced_rushing (1,869 rows): yards before contact, YAC, broken tackles

**Current Usage**: ❌ NOT USED

**Potential Features** (aggregate to team-level):
```
Defense:
- completion% allowed (pass defense quality)
- yards per target allowed (efficiency)
- blitz rate, pressure rate
- yards after catch allowed (tackling quality)

Passing:
- average depth of target (ADOT) - offensive aggression
- air yards vs YAC split (play style indicator)
- batted pass rate (OL quality)
- drop rate (receiving corps quality)

Rushing:
- yards before contact (OL quality)
- yards after contact (RB quality)
- broken tackles rate (RB elusiveness)
```

#### Opportunity 4: Add Team Records & Standings
**Available**: ESPN API now populates:
- home_record_wins, home_record_losses
- away_record_wins, away_record_losses

**Current Usage**: ❌ NOT USED (just added in Phase 1)

**Potential Features**:
```
- Win percentage (team quality indicator)
- Home/away win percentage split
- Recent form (last 5 games record)
- Strength of schedule adjustment
```

#### Opportunity 5: Utilize Odds Team Games
**Available**: odds_team_games (544 rows) with:
- close_spread_team (team-specific spread)
- vs_line (actual performance vs spread)
- ou_result (over/under result)

**Current Usage**: ❌ NOT USED (model uses main odds table only)

**Potential Features**:
```
- Season ATS (against the spread) record
- Season O/U (over/under) record
- Recent ATS performance (indicator of market inefficiency)
- Closing line value (sharp money indicator)
```

---

## 4. Feature Engineering Opportunities

### Advanced Momentum Features
**Current**: EMA, trend, volatility, season avg, recent ratio  
**Missing**:
```python
# 1. Streak indicators
- Current win/loss streak
- Scoring streak (25+ points in N consecutive games)
- Defensive streak (held under X points)

# 2. Performance decay
- Weighted average with exponential decay (recent games worth more)
- Already implemented as EMA, but could add multiple span lengths

# 3. Matchup-specific history
- Head-to-head record (last 3 years)
- Performance vs similar opponents (division rivals, same defensive scheme)

# 4. Situational splits
- Performance in prime time games (already have broadcast_primetime column)
- Performance by temperature range (<32°F, 32-50°F, >50°F)
- Performance by precipitation (dry, rain, snow)
```

### Interaction Features (Beyond Phase 1)
**Current Phase 1**: 16 interaction features (pressure advantage, turnover impact, etc.)  
**Phase 2 (Placeholder)**: Opponent-adjusted metrics

**Suggested Phase 2 Enhancements**:
```python
# 1. Strength of Schedule Adjustments
- Offensive yards per play adjusted by opponent defensive rank
- Defensive yards allowed adjusted by opponent offensive rank
- Formula: Adjusted = Raw × (League_Avg / Opponent_Avg)

# 2. Pace-Adjusted Stats
- Possessions per game (team tempo indicator)
- Points per possession (efficiency independent of pace)
- Opponent pace adjustment (fast offense vs slow defense = more possessions)

# 3. Matchup Advantages
- Pass offense efficiency vs Pass defense efficiency
- Rush offense efficiency vs Rush defense efficiency  
- Blitz rate vs pressure allowed rate (identify vulnerabilities)

# 4. Game Script Predictors
- Team tends to lead? (avg point differential by quarter)
- Team tends to trail? (comebacks, garbage time stats)
- Score-dependent play calling (rush% when leading vs trailing)
```

### Market-Based Features (Enhanced)
**Current**: Spread, total, movement, implied probability  
**Available but unused**:
```python
# From odds_team_games:
- ATS record (betting market performance)
- O/U record (total scoring tendency)

# Potential new features:
- Public betting % vs line movement (sharp money detector)
- Opening line vs consensus (where did line open relative to market)
- Cross-book spread variance (disagreement = uncertainty)
- Historically overvalued teams (market bias)
```

---

## 5. Model Architecture Opportunities

### Current Model: model_v3.py
**Strengths**:
- Momentum features (v3 enhancement)
- Phase 1 interaction features
- Market integration (odds)
- Ensemble option (RF + GradientBoosting)

**Weaknesses**:
- Missing weather data (model expects it)
- Only uses 12% of available games (team_games gap)
- Phase 2 opponent adjustments not implemented
- No use of PFR advanced stats (9,000+ rows available)

### Alternative Model: model_v4.py
**Purpose**: Uses PFR team stats (season-level)  
**Data**: pfr_team_stats_historical (160 rows)  
**Approach**: Merges season stats for home/away teams, creates differentials

**Status**: Exists but appears to be secondary/experimental

### Recommended Hybrid Approach
```
1. Backfill team_games from pfr_gamelogs (546 rows → 3,048 rows)
2. Add season-level baselines from pfr_team_stats (v4 approach)
3. Keep game-level rolling features (v3 momentum)
4. Integrate advanced PFR stats as aggregated features
5. Add weather + rest days
6. Implement full Phase 2 opponent adjustments
```

**Expected Impact**:
- Current MAE (margin): ~10-11 pts
- With full implementation: **Target MAE: 8-9 pts** (-2 pts improvement)

---

## 6. Data Backfill Action Plan

### Priority 1: CRITICAL (Do Before HOU Prediction)
```
✅ 1. Backfill Weather Data
   Script: backfill_weather.py (or create new)
   Source: NOAA API, Weather Underground, or ESPN weather archive
   Target: 2020-2025 outdoor games (~1,800 games)
   Time: 2-4 hours (API calls + processing)
   Impact: -0.5 to -1.0 pts MAE

✅ 2. Calculate Rest Days
   Script: calculate_rest_days.py
   Source: games.game_date column
   Logic: Sort by team, compute date differences
   Time: 15 minutes
   Impact: -0.2 to -0.3 pts MAE

✅ 3. Populate team_games from PFR Gamelogs
   Script: migrate_pfr_to_team_games.py
   Source: pfr_team_gamelogs (3,048 rows)
   Target: team_games table (546 → 3,048 rows)
   Mapping:
     - pts_off → points_for
     - pts_def → points_against
     - yards_off → total_yards
     - to_off → turnovers_give
     - to_def → turnovers_take
   Time: 30 minutes
   Impact: -1.0 to -2.0 pts MAE (10x training data!)
```

### Priority 2: HIGH VALUE (This Week)
```
⏳ 4. Enrich ESPN Odds for All Current Games
   Script: enrich_espn_odds.py (already created)
   Action: Run for all Week 19/Playoffs games
   Time: 10 minutes
   Impact: Current game context

⏳ 5. Add Season Baseline Features (v4 integration)
   Script: merge_season_stats.py
   Source: pfr_team_stats (160 rows)
   Target: New features in prediction pipeline
   Time: 1 hour
   Impact: -0.3 to -0.5 pts MAE

⏳ 6. Implement Phase 2 Opponent Adjustments
   Script: Modify model_v3.py _add_phase2_features()
   Logic: Adjust offensive stats by opponent defensive rank
   Time: 2 hours
   Impact: -0.2 to -0.4 pts MAE
```

### Priority 3: NICE TO HAVE (Next Week)
```
📋 7. Aggregate Advanced PFR Stats
   Script: aggregate_pfr_advanced.py
   Source: pfr_advanced_* tables (9,000+ rows)
   Target: Team-level aggregates per season
   Time: 3 hours
   Impact: -0.1 to -0.3 pts MAE

📋 8. Add Market Performance Features
   Script: calculate_ats_ou_records.py
   Source: odds_team_games
   Target: Season ATS/OU records
   Time: 1 hour
   Impact: -0.1 to -0.2 pts MAE

📋 9. Create Situational Splits
   Script: add_situational_features.py
   Logic: Prime time record, temperature splits, etc.
   Time: 2 hours
   Impact: -0.1 to -0.2 pts MAE
```

---

## 7. Immediate Action Items (Before HOU Prediction)

### TODAY (Required):
1. **Backfill Weather** - Run NOAA API for 2020-2025 outdoor games
2. **Calculate Rest Days** - Simple SQL date arithmetic
3. **Populate team_games from PFR** - Unlock 3,048 gamelogs vs current 546

### TOMORROW MORNING (Before HOU):
4. **Enrich HOU@PIT Odds** - Run ESPN enrichment script
5. **Test Model** - Verify all features populated correctly
6. **Run Prediction** - HOU@PIT with complete data

### THIS WEEK (Post-HOU):
7. **Implement Phase 2 Adjustments** - Opponent-adjusted metrics
8. **Add Season Baselines** - Integrate pfr_team_stats (v4 approach)
9. **Retrain Model** - With full feature set
10. **Evaluate Improvement** - Compare MAE before/after

---

## 8. Expected Accuracy Improvements

### Current State (Estimated):
- **Margin MAE**: ~10-11 pts
- **Training Data**: 273 games (12% of available)
- **Features**: ~300 (missing weather, rest days)
- **Data Quality**: 0% weather, 0% rest days

### After Priority 1 Fixes:
- **Margin MAE**: ~8-9 pts ✅ **Target**
- **Training Data**: 1,524 games (66% of available)
- **Features**: ~320 (weather + rest days added)
- **Data Quality**: 80% weather, 100% rest days

### After Priority 2 Enhancements:
- **Margin MAE**: ~7.5-8.5 pts 🎯 **Optimized**
- **Training Data**: 1,524 games + season baselines
- **Features**: ~400 (opponent adjustments, season stats)
- **Data Quality**: 80% weather, 100% rest days, full team stats

### Industry Benchmarks:
- **Vegas Lines**: ~10-11 pts MAE (established baseline)
- **Top Models**: ~8-9 pts MAE (538, FPI)
- **Elite Models**: ~7-8 pts MAE (private/professional models)

**Goal**: Match or beat 538/FPI accuracy (~8 pts MAE)

---

## 9. Technical Debt & Cleanup

### Code Issues:
1. **Phase 2 Placeholder**: `_add_phase2_features()` does nothing (returns input unchanged)
2. **Feature Column Confusion**: Fixed in v3 but ensure all references use `_X_cols`
3. **Excel vs SQLite Paths**: Dual support adds complexity, consider SQLite-only
4. **Duplicate Stats**: Multiple tables with same data (offense_team_games vs team_games)

### Data Schema Issues:
1. **Inconsistent Naming**: Some tables use `is_home_0_1`, others use `is_home (0/1)`
2. **Redundant Tables**: moneylines_source vs odds (same data, different formats)
3. **Missing Relationships**: No foreign keys, manual merging required
4. **Column Proliferation**: games table has 50 columns (hard to maintain)

### Recommended Refactoring:
```sql
-- Consolidate team game stats into single normalized table
CREATE TABLE team_game_stats (
    game_id TEXT,
    team TEXT,
    is_home INTEGER,
    -- Core stats
    points INTEGER,
    total_yards INTEGER,
    turnovers INTEGER,
    -- Offensive stats
    pass_yds, rush_yds, plays, yards_per_play,
    -- Defensive stats  
    sacks_made, hurries_made, blitzes_sent,
    -- Advanced stats
    exp_pts_off, exp_pts_def,
    -- Metadata
    source TEXT,
    source_date DATE,
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);

-- Single odds table with all sources
CREATE TABLE odds_unified (
    game_id TEXT,
    provider TEXT,  -- 'pfr', 'espn', 'consensus'
    open_spread_home REAL,
    close_spread_home REAL,
    open_total REAL,
    close_total REAL,
    -- etc
);
```

---

## 10. Next Steps

### Immediate (Today):
- [x] Complete this analysis document
- [ ] Review with stakeholders
- [ ] Prioritize backfill tasks
- [ ] Start weather data collection

### Short-term (This Week):
- [ ] Execute Priority 1 backfills (weather, rest, team_games)
- [ ] Run HOU@PIT prediction with enhanced data
- [ ] Measure accuracy improvement
- [ ] Document results

### Medium-term (Next 2 Weeks):
- [ ] Implement Priority 2 enhancements (season baselines, Phase 2 adjustments)
- [ ] Retrain model with full feature set
- [ ] Evaluate on historical test set
- [ ] Compare vs Vegas accuracy

### Long-term (This Month):
- [ ] Integrate advanced PFR stats (Priority 3)
- [ ] Refactor data schema (normalize tables)
- [ ] Build automated backfill pipeline
- [ ] Create model evaluation dashboard
- [ ] Document feature importance rankings

---

## Appendix: Quick Reference

### Key Files
```
Models:
- src/models/model_v3.py - Production model (momentum features)
- src/models/model_v4.py - Experimental (season stats)

Data:
- data/nfl_model.db - SQLite database (2,331 games)
- data_inventory.json - Complete table catalog

Scripts:
- analyze_model_data.py - Database inventory tool
- enrich_espn_odds.py - ESPN API enrichment
- migrate_phase1_odds.py - Schema migration

Reports:
- WEATHER_IMPACT_ANALYSIS.md - Weather correlation study
- POSTGAME_ANALYSIS_2026-01-10.md - Recent predictions
```

### Database Quick Stats
```
Total Tables: 43
Total Games: 2,331 (2020-2025)
Team Game Records: 546 (need 4,662)
Odds Records: 276 (12% coverage)
PFR Gamelogs: 3,048 (untapped)
Advanced Stats: 9,000+ rows (untapped)
```

### Critical Gaps Summary
| Gap | Current | Target | Impact |
|-----|---------|--------|--------|
| Weather | 0% | 80% | -0.5 to -1.0 pts MAE |
| Rest Days | 0% | 100% | -0.2 to -0.3 pts MAE |
| team_games Coverage | 12% | 66% | -1.0 to -2.0 pts MAE |
| **TOTAL** | **Baseline** | **Enhanced** | **-1.7 to -3.3 pts MAE** 🎯 |

---

**END OF ANALYSIS**
