# Pro Football Reference Data Integration Guide

## What PFR Provides & How to Access It

### Currently Accessible Data Types

#### 1. **Snap Count Data** (HIGH VALUE)
- **Location**: /years/YYYY/snaps/ section
- **Availability**: Weekly snap counts by position
- **Data Points**:
  - QB snap counts
  - RB snap counts (rushing backs)
  - WR snap counts (wide receivers)
  - TE snap counts (tight ends)
  - OL snap counts
  - Pass rusher snap counts
  - Coverage cornerback snap counts
- **Scrape-ability**: Moderate (table-based HTML)
- **Value**: Predicts play-calling tendencies, personnel risk

**Example Use**: If a team's #1 WR is injured, snap count data shows #2 WR's actual targets vs expectation

---

#### 2. **Game Logs** (HIGH VALUE)
- **Location**: /players/YEAR/gamelogs
- **Availability**: Every player's per-game stats
- **Data Points**:
  - Passing yards, completions, TD, INT
  - Rushing attempts, yards, TD
  - Receiving targets, catches, yards, TD
  - Tackles, sacks, forced fumbles
  - Team wins/losses each game
- **Scrape-ability**: High (structured tables)
- **Value**: Track performance streaks, weather impact, opponent quality

**Example Use**: See if QB threw more TDs on grass vs turf, or if team runs more when facing strong pass rush

---

#### 3. **Red Zone Data** (MEDIUM VALUE)
- **Location**: /years/YYYY/red-zone-play-finder
- **Availability**: Play-by-play in red zone with outcomes
- **Data Points**:
  - TD vs FG ratio by team
  - Red zone efficiency %
  - Plays per TD
  - Down and distance in red zone
- **Scrape-ability**: Medium (depends on site structure)
- **Value**: Separates efficient teams from inefficient close-call teams

**Example Use**: Team A converts 70% of RZ trips to TD, Team B only 45%. Team A worth +3 pts in close games

---

#### 4. **Injury Data** (HIGH VALUE, SPARSE)
- **Location**: /players/injuries or boxscore pages
- **Availability**: Limited historical data (more recent is better)
- **Data Points**:
  - Out, Doubtful, Questionable, Day-to-day
  - Player name, position, team
  - Injury type (hamstring, ACL, etc.)
  - Date
- **Scrape-ability**: Low (scattered across pages)
- **Value**: Huge impact on QB/star player availability

**Example Use**: Mahomes ruled out → get backup Jimmy Garoppolo projection instead

---

#### 5. **Advanced Defense Metrics** (MEDIUM VALUE)
- **Location**: /years/YYYY/opp_* files (opp_pass, opp_rush, etc.)
- **Availability**: Offensive stats allowed by team
- **Data Points**:
  - Pass defense (yards allowed, completion %, TD allowed)
  - Rush defense (yards allowed, TD allowed)
  - Pressure rate forced on QB
  - Blitz rate
- **Scrape-ability**: High (structured tables)
- **Value**: Already partially integrated, add granularity

**Example Use**: Defense A allows 5.5 yds/carry but generates 12% pressure - worse than raw yards suggest

---

#### 6. **Drive Data** (MEDIUM VALUE)
- **Location**: Play-by-play with drive context
- **Availability**: Weekly
- **Data Points**:
  - Drive length (plays, yards, time)
  - Starting field position
  - Drive result (TD, FG, punt, turnover)
  - Top of drive vs end of drive quality
- **Scrape-ability**: Medium (requires play-by-play parsing)
- **Value**: Shows time-of-possession strategy and execution

**Example Use**: Team runs short-drive offense (few plays, many yards) vs methodical offense

---

#### 7. **Vegas Line History** (MEDIUM VALUE)
- **Location**: Betting data (may need external source)
- **Availability**: Opening and closing lines
- **Data Points**:
  - Opening spread
  - Closing spread
  - Difference (sharp money signal)
- **Scrape-ability**: Low (not directly on PFR, may need ESPN/covers.com)
- **Value**: Separates pro perception from model perception

**Example Use**: Line moves 2 pts towards Dogs after line open → likely sharp money on Dogs

---

#### 8. **Play-by-Play Context** (HIGH VALUE)
- **Location**: /boxscores/ pages
- **Availability**: Every play of every game
- **Data Points**:
  - Play type (pass, run, FG attempt, punt)
  - Down and distance
  - Result
  - Score differential at time
  - Time remaining
- **Scrape-ability**: Medium (HTML tables)
- **Value**: Enables game script reconstruction and situation analysis

**Example Use**: See if team is pass-happy when trailing vs running clock games

---

#### 9. **Team Records & Streaks** (LOW-MEDIUM VALUE)
- **Location**: Various schedule pages
- **Availability**: Weekly update
- **Data Points**:
  - Win/loss streak
  - Conference record
  - Division record
  - Home/away record
- **Scrape-ability**: High
- **Value**: Quick trend detection

---

#### 10. **Playoff Performance History** (MEDIUM VALUE)
- **Location**: /playoffs/ section
- **Availability**: Historical (2020-2025)
- **Data Points**:
  - Playoff record by team
  - Home court advantage in playoffs
  - Seed performance
  - Matchup history
- **Scrape-ability**: High (structured)
- **Value**: Seeding effects, pressure/momentum factors

---

## Recommended Scraping Priorities

### Priority 1: SNAP COUNTS (Highest ROI)
```
URL Pattern: https://www.pro-football-reference.com/years/2025/snaps/
Tables to Extract:
  - Offensive snap counts (QB, RB, WR, TE, OL)
  - Defensive snap counts (Pass rushers, CBs, Safeties)

Frequency: Weekly (once available)
Historical Data: Available for 2015-2025
Data Quality: Excellent
Implementation Difficulty: Low-Medium
```

### Priority 2: INJURY DATA (Highest Impact)
```
URL Pattern: https://www.pro-football-reference.com/years/YYYY/injuries/
Data Points:
  - Player name, team, position
  - Injury type (ACL, hamstring, etc.)
  - Status (Out, Doubtful, Questionable)
  - Date

Frequency: Real-time (before games)
Historical Data: Spotty for 2020-2023, good for 2024-2025
Data Quality: Variable
Implementation Difficulty: Medium (scattered format)
```

### Priority 3: RED ZONE PLAY FINDER (High Impact)
```
URL Pattern: https://www.pro-football-reference.com/years/YYYY/red-zone-play-finder/
Data Points:
  - TD vs FG by team
  - Conversion rates
  - Plays per TD

Frequency: Weekly
Historical Data: Available
Data Quality: Good
Implementation Difficulty: Medium
```

### Priority 4: GAME LOGS (Comprehensive)
```
URL Pattern: https://www.pro-football-reference.com/players/AAAA/
Data Points:
  - Per-game stats for all players
  - Enables validation of aggregates
  - Shows player performance vs weather/opponent

Frequency: After each game
Historical Data: Complete 2020-2025
Data Quality: Excellent
Implementation Difficulty: High (massive volume - 3000+ players × 16-17 games)
```

---

## External Data Sources to Consider

### ESPN
- **Vegas lines**: Opening, closing, movement
- **Vegas line historical**: Sharp money indicators
- **Weather updates**: Real-time conditions

### Vegas Insider / Covers.com
- **Line movement**: By minute (sharp vs public)
- **Consensus picks**: Aggregate prediction
- **Betting trends**: % of bets on each side

### NFL.com
- **Official injury reports**: Most reliable source
- **Snap counts**: Sometimes posted by team reports
- **Game logs**: Real-time updates

### NFLST (Statistical Tracker)
- **Air yards, YAC**: Receiving breakdown
- **Pressure stats**: QB pressure rates
- **GPS data**: Player speed/distance (premium)

---

## Implementation Strategy

### Phase 1: Build Snap Count Scraper (Week 1-2)
- Extract weekly snap counts
- Store in DB with player_id, team, position, week, snap_count, snap_pct
- Backfill 2020-2024
- Add to v3 model as feature (RB snap% vs WR snap% → run/pass indicator)

### Phase 2: Injury Data Integration (Week 2-3)
- Scrape injury pages for 2024-2025
- Manual backfill for 2020-2023 from news archives
- Store: player_id, team, week, injury_type, status, impact_level
- Use in predictions: Reduce expected scoring if key player out

### Phase 3: Red Zone Data (Week 3-4)
- Parse red zone play finder
- Store: team, season, rz_attempts, rz_td, rz_fg, rz_pct
- Calculate: TD conversion %, FG conversion %, scoring efficiency
- Add to features for close-game bias

### Phase 4: Game Log Aggregates (Week 4-6)
- Extract game logs for QBs, RBs, WRs, pass rushers
- Create per-game features (vs aggregate)
- Track performance trends, weather sensitivity
- Link to main game table

---

## Code Structure

```python
# New tables to add to nfl_model.db:
snap_counts_weekly
- game_id, team, player_id, position, snaps, snap_pct

player_injuries_weekly  
- game_id, team, player_id, injury_type, status, availability_0_1

red_zone_stats_seasonal
- season, team, rz_attempts, rz_td, rz_fg, rz_pct, rz_scoring_efficiency

player_game_logs
- game_id, player_id, team, position, stats (JSON)

# New scraping modules:
scripts/scrape_snap_counts.py
scripts/scrape_injuries.py  
scripts/scrape_red_zone.py
scripts/scrape_game_logs.py
scripts/scrape_vegas_lines.py
```

---

## Expected Impact on Model

**Current State:**
- Margin MAE: 1.86 pts (from recent 2-game sample)
- Using team-level aggregates + weather
- Missing: Player availability, snap context, situational detail

**After Phase 1 (Snap Counts):**
- Estimated Margin MAE: 1.65-1.75 pts (-0.1 to -0.2)
- Rationale: Better pass/run balance prediction

**After Phase 2 (Injuries):**
- Estimated Margin MAE: 1.50-1.65 pts (-0.15 to -0.25)
- Rationale: Massive swing when star QB/RB unavailable

**After Phase 3 (Red Zone):**
- Estimated Margin MAE: 1.40-1.55 pts (-0.10 to -0.20)
- Rationale: Better close-game scoring prediction

**After All Phases:**
- Target Margin MAE: 1.20-1.40 pts
- 25-35% improvement over baseline
- Estimated 0.5-0.7 points per game gained

