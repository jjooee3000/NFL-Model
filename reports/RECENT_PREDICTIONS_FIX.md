# Recent Predictions & Accuracy - Fixes Applied

## Issues Identified

### 1. **Ongoing Game Showing in Results**
- **Problem**: LAC@NE (currently live on 2026-01-12) was showing 5 times in the "Recent Predictions & Accuracy" table
- **Root Cause**: The query was selecting all games with scores, including today's games that are still in progress

### 2. **Multiple Rows for Same Event**
- **Problem**: Same game appearing multiple times in the table (e.g., LAC@NE appeared 5 times, with 19+ predictions in database)
- **Root Cause**: The prediction log contains multiple predictions per game (which is correct for tracking), but the UI was showing ALL predictions instead of just ONE per game

## Solution Applied

### Changes to `/src/nfl_model/services/api/app.py` (Lines 222-257)

**Before:**
```python
recent_rows = conn.execute("""
    SELECT 
        ep.game_id, ep.away_team, ep.home_team, ep.pred_margin_home, ep.pred_total, 
        ep.timestamp, g.away_score, g.home_score, g."game_date_yyyy-mm-dd"
    FROM ensemble_predictions ep
    JOIN games g ON ep.game_id = g.game_id
    WHERE g.away_score IS NOT NULL AND g.home_score IS NOT NULL
    ORDER BY g."game_date_yyyy-mm-dd" DESC, ep.timestamp DESC
    LIMIT 10
""").fetchall()
```

**After:**
```python
# Get today's date to filter out ongoing games
today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

recent_rows = conn.execute("""
    WITH LatestPredictions AS (
        SELECT 
            ep.game_id, 
            ep.away_team, 
            ep.home_team, 
            ep.pred_margin_home, 
            ep.pred_total,
            ep.timestamp,
            ROW_NUMBER() OVER (PARTITION BY ep.game_id ORDER BY ep.timestamp DESC) as rn
        FROM ensemble_predictions ep
    )
    SELECT 
        lp.game_id, lp.away_team, lp.home_team, lp.pred_margin_home, lp.pred_total, 
        lp.timestamp, g.away_score, g.home_score, g."game_date_yyyy-mm-dd"
    FROM LatestPredictions lp
    JOIN games g ON lp.game_id = g.game_id
    WHERE lp.rn = 1
        AND g.away_score IS NOT NULL 
        AND g.home_score IS NOT NULL
        AND g."game_date_yyyy-mm-dd" < ?
    ORDER BY g."game_date_yyyy-mm-dd" DESC
    LIMIT 10
""", (today,)).fetchall()
```

## Key Changes

### 1. **Date Filtering**
- Added `today = datetime.datetime.utcnow().strftime("%Y-%m-%d")` to get current date
- Added condition `AND g."game_date_yyyy-mm-dd" < ?` to exclude today's games
- **Result**: Ongoing games (like LAC@NE on 2026-01-12) are excluded

### 2. **Deduplication with Window Function**
- Used Common Table Expression (CTE) `LatestPredictions`
- Applied `ROW_NUMBER() OVER (PARTITION BY ep.game_id ORDER BY ep.timestamp DESC)` to rank predictions
- Filtered to only `WHERE lp.rn = 1` (most recent prediction per game)
- **Result**: Each game appears exactly once, showing the latest prediction

## Verification Results

### Before Fix:
```
1. 2025_W19_LAC_NE: LAC@NE pred:1.1 actual:9.0-3.0
2. 2025_W19_LAC_NE: LAC@NE pred:1.1 actual:9.0-3.0
3. 2025_W19_LAC_NE: LAC@NE pred:3.5 actual:9.0-3.0
4. 2025_W19_LAC_NE: LAC@NE pred:1.1 actual:9.0-3.0
5. 2025_W19_LAC_NE: LAC@NE pred:1.1 actual:9.0-3.0
... (all showing ongoing game with duplicates)
```

### After Fix:
```
1. 2025_W01_BUF_JAX: BUF@JAX pred:2.7 (completed 2026-01-11)
2. 2025_W19_GB_CHI: GB@CHI pred:0.7 (completed 2026-01-11)
3. 2025_W19_SF_PHI: SF@PHI pred:1.0 (completed 2026-01-11)
4. 2025_W19_LAR_CAR: LAR@CAR pred:1.0 (completed 2026-01-10)
```

✅ **LAC@NE removed** (ongoing game excluded)
✅ **No duplicates** (one row per game)
✅ **Only completed games** (all from previous days)

## Technical Notes

- **SQLite Version**: 3.37.2 (supports window functions since 3.25.0)
- **Window Function**: `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)` for deduplication
- **CTE Support**: Common Table Expressions (WITH clause) used for cleaner SQL
- **Date Comparison**: Uses string comparison for dates in YYYY-MM-DD format

## Testing

All tests passed:
- Query executed successfully
- Returns 4 unique completed games
- No LAC@NE in results (current date: 2026-01-12)
- Server running on http://127.0.0.1:8083
