# Data Enhancement Strategy: Summary

## Quick Reference - Most Important Missing Data

### Tier 1: MUST HAVE (Would add 0.3-0.5 pts margin improvement)

| Data Type | Current Status | Impact | Effort | Timeline |
|-----------|---|---|---|---|
| **Injury Reports** | 0 rows in DB | QB out = -10 to -15 pts swing | Medium | 1-2 weeks |
| **Snap Counts** | Not integrated | Reveals pass/run tendencies | Low | 1 week |
| **Red Zone Data** | Aggregate only | Separates TDs from FGs | Medium | 1 week |

### Tier 2: NICE-TO-HAVE (Would add 0.1-0.3 pts improvement)

| Data Type | Current Status | Impact | Effort | Timeline |
|-----------|---|---|---|---|
| **Vegas Line Movement** | Not tracked | Shows sharp money | Low | 2-3 days |
| **Game Script** | Not available | Changes play-calling | Medium | 2 weeks |
| **Strength of Schedule** | Not quantified | Context for results | Medium | 1 week |

---

## The 3 Most Impactful Additions

### #1: INJURY DATA
**What it is**: Player availability status each week

**Why it matters**: 
- Starting QB out = Team scoring drops 10-15 pts on average
- Star RB out = Run game loses 3-5 yards per carry
- WR1 out = Passing efficiency drops 5-8 pts

**Where to get it**:
- PFR /years/YYYY/injuries/
- NFL.com official injury reports
- ESPN injury tracker

**Current DB**: injuries_qb table exists but is EMPTY (0 rows)

**To implement**: 
1. Backfill 2020-2024 from news archives
2. Weekly scrape 2025 forward
3. Add to model: if key_player_out, reduce expected_pts by X

**Expected improvement**: -0.3 to -0.5 pts margin MAE

---

### #2: SNAP COUNTS
**What it is**: % of plays each player participates in each week

**Why it matters**:
- Pass snap % vs run snap % = game plan
- RB snap % drop = team switching to passing game
- CB snap % = defensive personnel grouping

**Where to get it**:
- PFR /years/YYYY/snaps/
- NFL.com sometimes posts weekly

**Current DB**: Not in database

**To implement**:
1. Scrape weekly snap counts by position
2. Store: team, position, game_id, snap_pct
3. Add to features: pass_snap_pct, rb_snap_pct, etc.
4. Use in momentum: teams increasing pass snaps trend toward higher scoring

**Expected improvement**: -0.1 to -0.2 pts margin MAE

---

### #3: RED ZONE EFFICIENCY  
**What it is**: TD vs FG conversion rates in red zone (20 yards or less from end zone)

**Why it matters**:
- Efficient teams convert 65-75% RZ trips to TDs
- Inefficient teams only 45-55%
- Explains scoring gap beyond total yards

**Where to get it**:
- PFR /years/YYYY/red-zone-play-finder/
- Already partially have seasonal data

**Current DB**: Aggregate seasonal data exists, need per-game

**To implement**:
1. Parse red zone play-by-play
2. Calculate team RZ TD%, FG%, efficiency
3. Build features: rz_td_efficiency, rz_fg_pct
4. Use in model: high-RZ-efficiency teams get +0.5 to +1.0 pts

**Expected improvement**: -0.1 to -0.2 pts margin MAE

---

## Secondary High-Value Additions

### Vegas Line Movement Tracking
- **What**: Opening line vs closing line difference
- **Why**: When line moves 2+ pts towards Dogs before kickoff = sharp money signal
- **Effort**: Low (automated tracking from espn/covers)
- **Impact**: -0.05 to -0.15 pts

### Game Script Context
- **What**: Score differential during game → passing/running ratio changes
- **Why**: Teams trailing throw more, teams ahead run more
- **Effort**: Medium (requires play-by-play parsing)
- **Impact**: -0.1 to -0.2 pts

### Player Game Logs
- **What**: Individual game performance for key players
- **Why**: Track momentum, weather sensitivity, opponent impact
- **Effort**: High (massive volume)
- **Impact**: -0.1 to -0.3 pts

---

## Database Schema Additions Needed

```sql
-- Table 1: Weekly Snap Counts
CREATE TABLE snap_counts_weekly (
    id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    team TEXT NOT NULL,
    position TEXT,  -- QB, RB, WR, TE, CB, EDGE, etc.
    snaps INTEGER,
    snap_pct REAL,
    FOREIGN KEY(game_id) REFERENCES games(game_id)
);

-- Table 2: Player Injuries
CREATE TABLE player_injuries_weekly (
    id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    team TEXT NOT NULL,
    player_name TEXT,
    position TEXT,
    injury_type TEXT,  -- ACL, hamstring, concussion, etc.
    status TEXT,  -- Out, Doubtful, Questionable
    availability FLOAT,  -- 0.0 (out) to 1.0 (active)
    impact_points FLOAT,  -- -15 to +0
    FOREIGN KEY(game_id) REFERENCES games(game_id)
);

-- Table 3: Red Zone Performance
CREATE TABLE red_zone_performance_weekly (
    id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    team TEXT NOT NULL,
    rz_attempts INTEGER,  -- >1 attempt in RZ (within 20 yds)
    rz_touchdowns INTEGER,
    rz_field_goals INTEGER,
    rz_turnovers INTEGER,
    rz_td_pct FLOAT,
    rz_scoring_efficiency FLOAT,  -- points per attempt
    FOREIGN KEY(game_id) REFERENCES games(game_id)
);

-- Table 4: Vegas Lines (for tracking movement)
CREATE TABLE vegas_lines_tracking (
    id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    timestamp DATETIME,
    sportsbook TEXT,
    opening_spread FLOAT,
    current_spread FLOAT,
    opening_total FLOAT,
    current_total FLOAT,
    line_movement_spread FLOAT,  -- current - opening
    FOREIGN KEY(game_id) REFERENCES games(game_id)
);
```

---

## Implementation Priority Matrix

```
        HIGH IMPACT
            ^
            |
    InjuryData  RedZone
       |         |
    SnapCounts   |
       |         |
EFFORT |    VegasMovement
       |         |
       +-------->
        LOW      HIGH
        
Top Priority (Do First):
1. Injury Data (if historical available)
2. Snap Counts (easier to scrape)
3. Red Zone (medium effort, high impact)
```

---

## Expected Results After Implementation

### Before Enhancement
```
Current Model (v3 with SQLite):
  Margin MAE: 1.86 pts (2-game sample)
  Total MAE: 12.50 pts
  Confidence: Moderate (missing key context)
```

### After Phase 1 (Injuries + Snap Counts)
```
Estimated Improvement:
  Margin MAE: 1.60-1.70 pts (-0.2 to -0.3)
  Total MAE: 11.50-12.00 pts
  Confidence: Higher (QB/availability visible)
  Timeline: 2 weeks
```

### After Phase 2 (Red Zone + Vegas)
```
Estimated Improvement:
  Margin MAE: 1.40-1.55 pts (-0.15 to -0.30 from phase 1)
  Total MAE: 10.50-11.50 pts
  Confidence: Significantly higher
  Timeline: +3 weeks
```

### After Phase 3 (Full Enhancement)
```
Target State:
  Margin MAE: 1.20-1.40 pts (-25% to -35% from baseline)
  Total MAE: 9.50-11.00 pts
  Confidence: High (comprehensive context)
  Timeline: +4-6 weeks additional
```

---

## Quick Win: Snap Count Integration

**Easiest first step:**

1. **Source**: PFR snap counts page
2. **Data**: Weekly position snaps (already scraped partially)
3. **Features to add**:
   - `pass_snap_pct` = QB + WR snaps / total
   - `rush_snap_pct` = RB snaps / total  
   - `snap_balance` = |pass_snap_pct - 0.5|
4. **Model impact**: Better call prediction, game plan visibility
5. **Effort**: 1 week

---

## File References Created

1. `PFR_DATA_GAPS_ANALYSIS.md` - Current state + missing data tiers
2. `PFR_INTEGRATION_ROADMAP.md` - Detailed implementation guide
3. This file: Quick reference summary

**Next step**: Pick one from Tier 1 to implement first (recommend: Snap Counts)

