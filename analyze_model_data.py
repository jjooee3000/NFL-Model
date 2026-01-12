"""
Comprehensive Model Analysis
=============================

This script analyzes:
1. What data sources we have
2. What data the model currently uses
3. What data is available but unused
4. Opportunities for improvement
"""

import sqlite3
import pandas as pd
from pathlib import Path
import json

print("="*80)
print("COMPREHENSIVE MODEL ANALYSIS")
print("="*80)

# 1. Database Tables Inventory
print("\n1. DATABASE TABLES INVENTORY")
print("-"*80)

conn = sqlite3.connect('data/nfl_model.db')

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
table_info = {}

for (table_name,) in tables:
    if table_name.startswith('sqlite_'):
        continue
    
    count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    table_info[table_name] = {
        'rows': count,
        'columns': len(cols),
        'column_names': [c[1] for c in cols]
    }

# Group tables by category
core_tables = ['games', 'team_games']
odds_tables = [t for t in table_info.keys() if 'odds' in t.lower() or 'moneyline' in t.lower()]
pfr_tables = [t for t in table_info.keys() if 'pfr' in t.lower()]
team_stat_tables = [t for t in table_info.keys() if 'team_game' in t and t not in core_tables]
other_tables = [t for t in table_info.keys() if t not in core_tables + odds_tables + pfr_tables + team_stat_tables]

print("\nCORE TABLES:")
for table in core_tables:
    if table in table_info:
        print(f"  {table}: {table_info[table]['rows']:,} rows, {table_info[table]['columns']} cols")

print("\nODDS/BETTING TABLES:")
for table in odds_tables:
    print(f"  {table}: {table_info[table]['rows']:,} rows, {table_info[table]['columns']} cols")

print("\nPRO FOOTBALL REFERENCE (PFR) TABLES:")
for table in pfr_tables:
    print(f"  {table}: {table_info[table]['rows']:,} rows, {table_info[table]['columns']} cols")

print("\nTEAM STATISTICS TABLES:")
for table in team_stat_tables:
    print(f"  {table}: {table_info[table]['rows']:,} rows, {table_info[table]['columns']} cols")

print("\nOTHER TABLES:")
for table in other_tables:
    print(f"  {table}: {table_info[table]['rows']:,} rows, {table_info[table]['columns']} cols")

# 2. Check games table schema in detail
print("\n2. GAMES TABLE - DETAILED SCHEMA")
print("-"*80)
games_cols = conn.execute("PRAGMA table_info(games)").fetchall()
print(f"\nTotal columns in games table: {len(games_cols)}")

# Categorize columns
basic_cols = []
weather_cols = []
venue_cols = []
score_cols = []
odds_cols = []
new_cols = []

for col in games_cols:
    col_name = col[1]
    if 'weather' in col_name or 'temp' in col_name or 'wind' in col_name or 'precip' in col_name or 'humid' in col_name or 'cloud' in col_name or 'pressure' in col_name:
        weather_cols.append(col_name)
    elif 'odds' in col_name or 'spread' in col_name or 'moneyline' in col_name:
        odds_cols.append(col_name)
    elif col_name in ['game_id', 'season', 'week', 'away_team', 'home_team', 'game_date_yyyy-mm-dd', 'game_datetime', 'kickoff_time_local', 'seasontype']:
        basic_cols.append(col_name)
    elif 'score' in col_name or 'point' in col_name or 'total' in col_name:
        score_cols.append(col_name)
    elif 'stadium' in col_name or 'surface' in col_name or 'roof' in col_name or 'indoor' in col_name or 'neutral' in col_name or 'city' in col_name or 'state' in col_name:
        venue_cols.append(col_name)
    elif col_name in ['attendance', 'broadcast_network', 'broadcast_primetime', 'home_record_wins', 'home_record_losses', 'away_record_wins', 'away_record_losses']:
        new_cols.append(col_name)
    else:
        basic_cols.append(col_name)

print("\nBasic Info:", basic_cols)
print(f"\nWeather ({len(weather_cols)}):", weather_cols)
print(f"\nVenue ({len(venue_cols)}):", venue_cols)
print(f"\nScore/Outcome ({len(score_cols)}):", score_cols)
print(f"\nOdds (NEW - {len(odds_cols)}):", odds_cols)
print(f"\nPhase 1 Additions ({len(new_cols)}):", new_cols)

# 3. Sample data quality check
print("\n3. DATA QUALITY ASSESSMENT")
print("-"*80)

# Check how much data we have for recent games
recent_games = conn.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN home_score IS NOT NULL THEN 1 ELSE 0 END) as with_scores,
        SUM(CASE WHEN weather_temp_f IS NOT NULL THEN 1 ELSE 0 END) as with_weather,
        SUM(CASE WHEN away_rest_days IS NOT NULL THEN 1 ELSE 0 END) as with_rest
    FROM games
    WHERE season >= 2020
""").fetchone()

print(f"\nGames since 2020:")
print(f"  Total: {recent_games[0]:,}")
print(f"  With scores: {recent_games[1]:,} ({recent_games[1]/recent_games[0]*100:.1f}%)")
print(f"  With weather: {recent_games[2]:,} ({recent_games[2]/recent_games[0]*100:.1f}%)")
print(f"  With rest days: {recent_games[3]:,} ({recent_games[3]/recent_games[0]*100:.1f}%)")

# 4. Check what team-level statistics are available
print("\n4. TEAM-LEVEL STATISTICS AVAILABLE")
print("-"*80)

for table in team_stat_tables:
    if table_info[table]['rows'] > 0:
        print(f"\n{table} ({table_info[table]['rows']:,} rows):")
        cols = table_info[table]['column_names']
        # Show interesting columns (skip team, game_id, season, week)
        interesting = [c for c in cols if c not in ['team', 'team_pfr', 'game_id', 'season', 'week', 'opponent']]
        if len(interesting) <= 10:
            print(f"  Columns: {', '.join(interesting)}")
        else:
            print(f"  {len(interesting)} columns including: {', '.join(interesting[:8])}...")

# 5. Check PFR data availability
print("\n5. PRO FOOTBALL REFERENCE DATA")
print("-"*80)

for table in pfr_tables[:10]:  # Show first 10
    if table_info[table]['rows'] > 0:
        sample = conn.execute(f"SELECT * FROM {table} LIMIT 1").fetchone()
        print(f"\n{table}: {table_info[table]['rows']:,} rows, {table_info[table]['columns']} cols")

# 6. Check odds table
print("\n6. BETTING LINES DATA")
print("-"*80)

if 'odds' in table_info:
    odds_sample = conn.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT game_id) as unique_games,
            SUM(CASE WHEN close_spread_home IS NOT NULL THEN 1 ELSE 0 END) as with_spread,
            SUM(CASE WHEN close_total IS NOT NULL THEN 1 ELSE 0 END) as with_total
        FROM odds
    """).fetchone()
    
    print(f"\nOdds table:")
    print(f"  Total rows: {odds_sample[0]:,}")
    print(f"  Unique games: {odds_sample[1]:,}")
    print(f"  With spread: {odds_sample[2]:,}")
    print(f"  With total: {odds_sample[3]:,}")

# 7. Save detailed inventory to JSON
print("\n7. SAVING DETAILED INVENTORY")
print("-"*80)

inventory = {
    'generated': pd.Timestamp.now().isoformat(),
    'total_tables': len(table_info),
    'tables': {}
}

for table, info in table_info.items():
    inventory['tables'][table] = {
        'rows': info['rows'],
        'columns': info['columns'],
        'sample_columns': info['column_names'][:20]  # First 20 columns
    }

with open('data_inventory.json', 'w') as f:
    json.dump(inventory, f, indent=2)

print("\n✓ Saved detailed inventory to data_inventory.json")

conn.close()

print("\n" + "="*80)
print("ANALYSIS COMPLETE - See data_inventory.json for full details")
print("="*80)
