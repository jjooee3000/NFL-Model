# Data Gap Analysis & PFR Enhancement Strategy

## Current Database State

**Current Coverage:**
- 26 tables, 573 columns
- 1,690 games (2020-2025)
- Comprehensive team-level stats
- Player-level advanced stats (4,989 defensive players, 2,687 receivers, 1,869 rushers, 553 passers)
- Seasonal aggregates and situational data

**What We Have:**
✓ Game fundamentals (scores, dates, weather, rest days)
✓ Team offensive/defensive metrics
✓ EPA and advanced efficiency metrics
✓ Turnover data
✓ Pass rush metrics (sacks, pressures, blitzes)
✓ Penalties and special teams
✓ Betting odds (opening/closing spreads, moneylines)
✓ 3rd/4th down conversion rates
✓ Red zone and drive statistics
✓ Individual player advanced stats

---

## Critical Missing Data Points

### Tier 1: HIGH IMPACT (Would significantly improve predictions)

1. **Injury Data** (Currently 0 rows in injuries_qb table)
   - QB injury status and availability
   - Impact on game day starter vs backup
   - Why it matters: QB changes are massive swing factors
   - Example: A backup QB starting drops team scoring by 10-20%

2. **Game Script Context**
   - Snap counts (pass vs run usage)
   - Play-calling tendencies by game situation
   - Lead/deficit sizes and how teams respond
   - Why it matters: Garbage time vs close game stats are very different

3. **Red Zone Efficiency Details**
   - Touchdowns vs field goals by drive
   - Conversion % by distance
   - Goal-to-go success rates
   - Why it matters: Critical for close game prediction

4. **Player Usage & Depth**
   - Snap counts for key players (QB, RB, WR, Pass rushers)
   - Starter vs backup performance splits
   - Key player absences
   - Why it matters: Star player availability changes everything

5. **Strength of Schedule Context**
   - Opponent strength rankings at time of game
   - Quality-of-opponent adjustments
   - Remaining SOS for betting implications
   - Why it matters: Context for team performance

### Tier 2: MEDIUM IMPACT (Would add clarity/nuance)

6. **Vegas Line Movement**
   - Opening line vs closing line changes
   - Public betting percentages
   - Where professional money landed
   - Why it matters: Sharps vs squares visible in line movement

7. **Drive-Level Details**
   - Average starting field position
   - Drive length distribution
   - Time per drive
   - Why it matters: Ball control visible in aggregate drives

8. **Air Yards & Yards After Catch Splits**
   - Already have some defense data
   - Need offensive split by receiver
   - Screen vs deep ball tendencies
   - Why it matters: Game plan visibility

9. **Back-to-Back Game Effects**
   - Days of rest tracking
   - Historical performance degradation
   - Travel distance impact
   - Why it matters: Cumulative fatigue is real

10. **Division Metrics**
    - Within-division performance vs rest of league
    - Conference strength variations
    - Head-to-head history
    - Why it matters: Division games are different

### Tier 3: NICE-TO-HAVE (Optimization/refinement)

11. Personnel groupings (11, 12, 21 personnel)
12. Defensive scheme indicators (coverage types, blitz %s)
13. Stadium-specific effects (grass vs turf, open vs domed)
14. Bye week effects on following week
15. Weather impact by outdoor/indoor status (already have this)

---

## PFR Data Sources to Integrate

### What PFR Provides (Publicly Available)

**Currently Integrated:**
- Team seasonal stats
- Player advanced stats
- Game logs
- Situational data (3rd down, red zone, scoring)
- Defense advanced metrics

**Available But Not Integrated:**
- **Schedule & Results**: https://www.pro-football-reference.com/years/YYYY/
- **Drive Charts**: Play-by-play with drive context
- **Box Scores**: Detailed game-by-game stats
- **Snap Counts**: https://www.pro-football-reference.com/years/YYYY/snaps/ (if available)
- **Injury Reports**: (Limited - mainly historical)
- **Team Game Logs**: Detailed per-game breakdowns
- **Playoff Records**: https://www.pro-football-reference.com/playoffs/
- **Head-to-Head**: Historical matchup data

**Scrapin-Friendly (2025 easier than historical):**
- Game weather details (wind direction, conditions)
- Attendance figures
- Vegas lines (if cached on site)
- Coaching changes/staff
- Play-by-play context

---

## Implementation Roadmap

### Phase 1: High-Value Quick Wins (1-2 weeks)
1. Fill injuries_qb table with available historical data
2. Add snap count percentages (pass vs run)
3. Red zone TD conversion rates

### Phase 2: Medium-Value Integration (2-4 weeks)
4. Vegas line movement tracking (new games going forward)
5. Game script context (lead size at each quarter)
6. Division/conference strength rankings

### Phase 3: Deep Enhancement (4-8 weeks)
7. Player snap counts by position
8. Drive-level detail extraction
9. Historical playoff data consolidation

### Phase 4: Continuous Collection (Ongoing)
10. Real-time injury updates
11. Weather updates (already doing)
12. Vegas line movement (for future seasons)

---

## Data Quality Notes

**Good:**
- Weather data well-integrated
- Team stats comprehensive
- EPA metrics reliable
- Advanced defense stats detailed

**Gaps:**
- injuries_qb table empty (0 rows) - needs backfill
- Player-level data has 2025 only mostly
- No individual player game logs (only season)
- Vegas lines only for 2025 forward

**Next Steps:**
1. Backfill injuries_qb for 2020-2024
2. Extract snap counts for 2020-2025
3. Add red zone detail
4. Implement quarterly game script tracking

---

## Estimated Impact by Adding Each

| Data Type | Margin MAE Improvement | Effort | Priority |
|-----------|------------------------|--------|----------|
| Injury data | -0.5 to -1.0 pts | Medium | HIGH |
| Snap count % | -0.2 to -0.4 pts | Low | HIGH |
| Red zone detail | -0.3 to -0.6 pts | Medium | HIGH |
| Game script | -0.2 to -0.3 pts | Medium | MEDIUM |
| Vegas movement | -0.1 to -0.2 pts | Low | MEDIUM |
| Strength of schedule | -0.2 to -0.4 pts | Medium | MEDIUM |

**Current v3 Margin MAE: 1.86 pts** (from recent playoff games)  
**Potential with all additions: ~0.5-1.0 pts (25-50% improvement)**

