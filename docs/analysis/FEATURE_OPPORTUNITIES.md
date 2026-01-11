# High-Impact Feature Engineering Opportunities

Based on correlation analysis of our 1,690-game database, here are **immediately actionable** improvements:

---

## 🔴 HIGH PRIORITY (Implement First)

### 1. **Feature Interactions** (Impact: +0.1-0.3 pts per interaction)

**What**: Multiplicative combinations of existing features that capture non-linear relationships

**Why**: A good offense vs bad defense = higher scoring than linear sum suggests

**Specific Interactions to Add**:
```python
# Matchup quality
df['matchup_epa'] = df['off_epa_rolling'] * df['def_epa_opp_rolling']

# Consistency score  
df['consistency'] = df['yards_per_play'] * df['success_rate']

# Weather-adjusted passing
df['weather_pass_penalty'] = df['pass_pct'] * df['wind_mph'] * (df['temperature'] < 40)

# Fatigue-adjusted HFA
df['tired_home_advantage'] = df['home_field_advantage'] / (1 + df['rest_days_deficit'])

# Dome team road weather penalty
df['dome_team_cold_penalty'] = df['is_dome_team'] * (df['temperature'] < 35) * df['is_away']
```

**Expected Impact**: -0.2 to -0.3 pts margin MAE

**Implementation Time**: ~2 hours (modify model_v3.py feature engineering)

---

### 2. **Opponent-Adjusted Stats** (Impact: +0.2-0.4 pts)

**What**: Normalize stats by opponent strength (300 yards vs #1 defense ≠ 300 yards vs #32 defense)

**Why**: Raw stats misleading without context of opponent quality

**How to Implement**:
```python
# Calculate opponent defensive rank each week
def calculate_opponent_adjusted_stats(df):
    # Rank defenses by yards allowed per game
    df['def_rank'] = df.groupby('week')['yards_allowed'].rank(ascending=True)
    
    # Adjust offensive stats
    df['yards_vs_rank'] = df['yards'] / (df['opp_def_rank'] / 16)  # Normalize to league average
    df['epa_vs_rank'] = df['epa_per_play'] / (df['opp_def_rank'] / 16)
    
    # Create "performance over expected" metric
    df['yards_over_expected'] = df['yards'] - df['expected_yards_vs_opp']
    
    return df
```

**Specific Features**:
- `yards_vs_def_rank` - Offensive yards adjusted for opponent defense quality
- `epa_vs_def_rank` - EPA adjusted for opponent
- `sack_rate_vs_pass_rush_rank` - How often sacked vs opponent's pass rush ability
- `completion_pct_vs_coverage_rank` - Passing efficiency vs opponent's secondary

**Expected Impact**: -0.2 to -0.4 pts margin MAE (especially in mismatch games)

**Implementation Time**: ~3 hours (requires ranking system + adjustment calculations)

---

## 🟡 MEDIUM PRIORITY (Add Next)

### 3. **Recent Game Exponential Weighting** (Impact: +0.1-0.2 pts)

**What**: Weight last 2 games more heavily than games 3-8 in rolling averages

**Why**: Team form changes - Week 18 performance more predictive than Week 10

**Current**: Equal weighting in 8-game window
```python
df['yards_rolling_8'] = df.rolling(8).mean()
```

**Improved**: Exponential decay
```python
# Half-life of 2 games (recent games weighted 4x more than old games)
weights = np.array([0.5**i for i in range(7, -1, -1)])  # [0.0078, 0.0156, ..., 0.5, 1.0]
weights = weights / weights.sum()

df['yards_ewm'] = df.rolling(8).apply(lambda x: (x * weights).sum())
```

**Implementation**: Modify `_calculate_rolling_features()` in model_v3.py

**Expected Impact**: -0.1 to -0.2 pts margin MAE

**Implementation Time**: ~1 hour

---

### 4. **Division Rivalry Flag** (Impact: +0.1-0.2 pts)

**What**: Binary flag for division games (NYG vs PHI, DAL vs WAS, etc.)

**Why**: Division games historically 2-3 pts lower scoring, more defensive

**How**:
```python
# Add division lookup
DIVISIONS = {
    'AFC_EAST': ['BUF', 'MIA', 'NWE', 'NYJ'],
    'AFC_NORTH': ['BAL', 'CIN', 'CLE', 'PIT'],
    'AFC_SOUTH': ['HOU', 'IND', 'JAX', 'TEN'],
    'AFC_WEST': ['DEN', 'KAN', 'LAC', 'LVR'],
    'NFC_EAST': ['DAL', 'NYG', 'PHI', 'WAS'],
    'NFC_NORTH': ['CHI', 'DET', 'GNB', 'MIN'],
    'NFC_SOUTH': ['ATL', 'CAR', 'NOR', 'TAM'],
    'NFC_WEST': ['ARI', 'LAR', 'SFO', 'SEA']
}

def is_division_game(team1, team2):
    for div, teams in DIVISIONS.items():
        if team1 in teams and team2 in teams:
            return True
    return False

df['is_division_game'] = df.apply(lambda row: is_division_game(row['home_team'], row['away_team']), axis=1)
```

**Expected Impact**: -0.1 to -0.2 pts total MAE

**Implementation Time**: ~30 min

---

### 5. **Betting Line Movement** (Impact: +0.15-0.25 pts)

**What**: Track opening line → closing line movement (sharp money indicator)

**Why**: Lines move >2 pts when sharp bettors identify value → those sides cover 55-60%

**Current State**: We have `odds` table but not tracking movement

**How**:
```python
# In odds table, calculate movement
df['line_movement'] = df['spread_close'] - df['spread_open']
df['big_movement'] = df['line_movement'].abs() > 2

# Add as feature
df['sharp_money_direction'] = np.sign(df['line_movement'])  # +1 or -1
df['sharp_money_magnitude'] = df['line_movement'].abs()
```

**Expected Impact**: -0.15 to -0.25 pts margin MAE (captures market wisdom)

**Implementation Time**: ~1 hour (need to populate opening/closing spreads)

---

### 6. **Venue-Specific Home Field Advantage** (Impact: +0.1-0.15 pts)

**What**: HFA varies by stadium (Arrowhead +4.2, Arizona +0.8)

**Why**: Not all home fields are equal - some stadiums have massive advantages

**How**:
```python
# Calculate from historical data
venue_hfa = games.groupby('venue')['margin'].mean()

# Add as feature
df['venue_hfa_adjustment'] = df['venue'].map(venue_hfa)
```

**Implementation**: Query database, create lookup table

**Expected Impact**: -0.1 to -0.15 pts margin MAE

**Implementation Time**: ~30 min

---

## 🟢 LOW PRIORITY (Nice to Have)

### 7. Primetime Performance Adjustment
- SNF/MNF/TNF games score differently (usually higher)
- Requires parsing game times

### 8. Surface Type (Grass vs Turf)
- Affects injury rates and scoring slightly
- Can pull from stadiums.py

### 9. Altitude Adjustment  
- Denver games affected by elevation
- Small effect (~1 pt)

---

## Implementation Roadmap

### Phase 1: Quick Wins (Week 1) - ~6 hours total
1. Feature Interactions (2 hrs) → +0.2-0.3 pts improvement
2. Division Rivalry Flag (30 min) → +0.1-0.2 pts improvement
3. Venue HFA Lookup (30 min) → +0.1-0.15 pts improvement
4. Recent Game Weighting (1 hr) → +0.1-0.2 pts improvement

**Expected Total: -0.5 to -0.85 pts margin MAE improvement**

### Phase 2: Data Enhancement (Week 2) - ~4 hours
5. Opponent-Adjusted Stats (3 hrs) → +0.2-0.4 pts improvement
6. Line Movement Tracking (1 hr) → +0.15-0.25 pts improvement

**Expected Total: -0.35 to -0.65 pts additional improvement**

### Combined Impact
- **Current MAE**: ~1.86 pts
- **After Phase 1**: ~1.0-1.4 pts (-0.5 to -0.85)
- **After Phase 2**: ~0.65-1.0 pts (-0.35 to -0.65 more)

**Target**: Sub-1.0 pt margin MAE (would be elite-level accuracy)

---

## Recommended Order

Start with **Feature Interactions** and **Division Games** - easiest to implement, decent impact.

Then add **Opponent-Adjusted Stats** - requires more work but highest single-feature impact.

Finally add **Line Movement** when we backfill opening/closing odds data.

---

## Code Structure

All of these can be added to `model_v3.py` in the feature engineering section:

```python
def _calculate_advanced_features(self, df):
    """Calculate high-impact derived features"""
    
    # 1. Feature interactions
    df = self._add_feature_interactions(df)
    
    # 2. Opponent adjustments
    df = self._add_opponent_adjusted_stats(df)
    
    # 3. Recent game weighting
    df = self._add_exponential_weighted_features(df)
    
    # 4. Division games
    df = self._add_division_flag(df)
    
    # 5. Venue HFA
    df = self._add_venue_hfa(df)
    
    return df
```

Each method isolated for easy testing/debugging.

---

**Next Step**: Want me to implement Phase 1 (Quick Wins) right now? Would take about 6 hours of coding but could improve predictions by 0.5-0.85 pts immediately.
