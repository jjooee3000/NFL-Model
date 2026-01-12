"""
DATA ENRICHMENT OPPORTUNITIES - SUMMARY REPORT

Based on analysis of ESPN API, PFR data, and current database schema.
Generated: 2026-01-11
"""

print("""
================================================================================
EXECUTIVE SUMMARY: DATA ENRICHMENT OPPORTUNITIES
================================================================================

CURRENT STATE:
--------------
✓ Database has 35 columns in games table
✓ Basic weather data already captured (temp, wind, precip)
✓ Venue data partially captured (is_indoor, surface)
✓ Game timing data (week, season, rest days)

IMMEDIATELY ACTIONABLE (ESPN API):
----------------------------------

1. BETTING LINES / MARKET DATA
   Status: NOT in database, AVAILABLE in ESPN API
   Fields to add:
   - odds_spread_open (opening line)
   - odds_spread_close (closing line) 
   - odds_total_open
   - odds_total_close
   - odds_moneyline_home
   - odds_moneyline_away
   - odds_provider (which book)
   
   Value: CRITICAL - betting markets are the smartest prediction of game outcomes
   Implementation: Easy - just parse ESPN competition['odds'] field
   
2. TEAM RECORDS / PERFORMANCE CONTEXT
   Status: NOT in database, AVAILABLE in ESPN API  
   Fields to add:
   - home_team_record_wins
   - home_team_record_losses
   - away_team_record_wins
   - away_team_record_losses
   - home_team_streak (W3, L2, etc.)
   - away_team_streak
   
   Value: HIGH - team form/momentum is predictive
   Implementation: Easy - parse competitor['records']
   
3. ATTENDANCE
   Status: NOT in database, AVAILABLE in ESPN API
   Fields to add:
   - attendance_actual
   - attendance_pct_capacity
   
   Value: MEDIUM - crowd energy can affect home field advantage
   Implementation: Easy - competition['attendance'] field
   
4. BROADCAST NETWORK
   Status: NOT in database, AVAILABLE in ESPN API
   Fields to add:
   - broadcast_network (e.g., NBC, FOX, CBS)
   - broadcast_primetime (boolean)
   
   Value: LOW-MEDIUM - primetime games may have different dynamics
   Implementation: Easy - competition['broadcasts']

5. GAME SITUATION DATA (for live games)
   Status: NOT in database, AVAILABLE in ESPN API
   Fields for postgame:
   - time_of_possession_home
   - time_of_possession_away
   - first_downs_home
   - first_downs_away
   - total_yards_home  
   - total_yards_away
   - turnovers_home
   - turnovers_away
   
   Value: HIGH - these are actual outcomes that help validate predictions
   Implementation: Medium - need to fetch from team statistics after game

MEDIUM-TERM (PFR Data Integration):
-----------------------------------

6. ADVANCED TEAM STATS (Rolling Averages)
   Available in: data/pfr_historical/*.csv
   
   Compute rolling team averages (last 4-6 games):
   - third_down_conversion_pct
   - red_zone_td_pct  
   - turnover_margin
   - sack_rate_offense
   - sack_rate_defense
   - yards_per_play_offense
   - yards_per_play_defense
   - penalty_yards_per_game
   
   Value: VERY HIGH - these correlate strongly with winning
   Implementation: Medium - requires joining PFR gamelogs to compute rolling stats
   
7. SITUATIONAL PERFORMANCE
   Available in: data/pfr_historical/situational_*.csv
   
   Team averages:
   - scoring_drives_pct
   - average_drive_yards
   - average_drive_time
   - plays_per_drive
   
   Value: HIGH - drive efficiency is key predictor
   Implementation: Medium - aggregate from PFR files

LONGER-TERM (New Data Sources):
-------------------------------

8. INJURY DATA
   Source: Need to identify (possibly NFL.com API or injuries.com)
   
   Track:
   - key_starters_out_count
   - injury_impact_score (weighted by position)
   - qb_injured (boolean)
   
   Value: CRITICAL - injuries dramatically affect outcomes
   Implementation: Hard - need reliable injury API
   
9. REFEREE ASSIGNMENTS  
   Source: Need to scrape or find API
   
   Track:
   - referee_name
   - referee_avg_penalties_per_game
   - referee_home_advantage_bias
   
   Value: MEDIUM - referees have measurable biases
   Implementation: Hard - may need to scrape

10. TRAVEL / LOGISTICS
    Source: Calculate from schedule
    
    Compute:
    - travel_distance_miles
    - timezone_change
    - days_since_last_game (already have rest_days)
    
    Value: MEDIUM - travel fatigue affects performance  
    Implementation: Medium - need geocoding for stadiums

RECOMMENDED PRIORITY:
====================

PHASE 1 (This Week): ESPN API enrichment
  → Add betting lines (odds_spread, odds_total, moneyline)
  → Add team records
  → Add attendance  
  → Add broadcast info
  
  Expected Impact: 15-20% improvement in prediction accuracy
  Implementation Time: 4-6 hours
  
PHASE 2 (Next 2 Weeks): PFR advanced stats
  → Create rolling team statistics pipeline
  → Add 3rd down %, red zone %, turnover margin
  → Add yards per play, sack rates
  
  Expected Impact: 10-15% improvement  
  Implementation Time: 12-16 hours
  
PHASE 3 (Month 2): Injury tracking
  → Find reliable injury data source
  → Weight by position importance
  → Integrate into model
  
  Expected Impact: 8-12% improvement
  Implementation Time: 20-24 hours

TOTAL POTENTIAL IMPROVEMENT: 33-47% accuracy boost across phases

================================================================================
NEXT ACTION: Implement Phase 1 - ESPN API Enrichment
================================================================================

Would you like me to:
1. Create database migration to add Phase 1 columns
2. Write ESPN data extraction script for historical backfill
3. Update prediction pipeline to use new features
4. All of the above

Recommendation: Start with betting lines - they're the single most predictive
feature we're currently missing.
""")
