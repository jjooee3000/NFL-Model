"""Check for existing odds data in database and PFR files"""
import sqlite3
import os
import pandas as pd

print("="*80)
print("CHECKING FOR EXISTING ODDS DATA")
print("="*80)

# 1. Check database for any odds-related columns
print("\n1. CURRENT DATABASE COLUMNS (checking for odds)")
print("-"*80)
conn = sqlite3.connect('data/nfl_model.db')
cursor = conn.execute('PRAGMA table_info(games)')
odds_columns = []
all_columns = []
for row in cursor:
    col_name = row[1]
    all_columns.append(col_name)
    if 'odds' in col_name.lower() or 'spread' in col_name.lower() or 'line' in col_name.lower():
        odds_columns.append(col_name)
        print(f"  ✓ Found: {col_name} ({row[2]})")

if not odds_columns:
    print("  ✗ No odds-related columns found in database")

# 2. Check for sample data in any odds columns
if odds_columns:
    print(f"\n2. SAMPLE DATA FROM EXISTING ODDS COLUMNS")
    print("-"*80)
    for col in odds_columns:
        result = conn.execute(f'SELECT COUNT(*) FROM games WHERE "{col}" IS NOT NULL').fetchone()
        print(f"  {col}: {result[0]} non-null rows")
        if result[0] > 0:
            sample = conn.execute(f'SELECT game_id, "{col}" FROM games WHERE "{col}" IS NOT NULL LIMIT 3').fetchall()
            for game_id, val in sample:
                print(f"    - {game_id}: {val}")

conn.close()

# 3. Check PFR files for odds data
print("\n3. PFR HISTORICAL FILES (checking for odds/lines)")
print("-"*80)
pfr_dir = 'data/pfr_historical'
if os.path.exists(pfr_dir):
    pfr_files = [f for f in os.listdir(pfr_dir) if f.endswith('.csv')]
    
    odds_files = []
    for f in pfr_files:
        if 'odds' in f.lower() or 'lines' in f.lower() or 'spread' in f.lower():
            odds_files.append(f)
    
    if odds_files:
        print(f"  Found {len(odds_files)} odds-related files:")
        for f in odds_files:
            print(f"    - {f}")
    else:
        print("  ✗ No odds-specific files found")
    
    # Check games files for odds columns
    print("\n  Checking games.csv files for odds columns:")
    games_files = [f for f in pfr_files if 'games' in f.lower()]
    for gf in games_files[:3]:  # Check first 3
        filepath = os.path.join(pfr_dir, gf)
        try:
            df = pd.read_csv(filepath, nrows=1)
            odds_cols = [c for c in df.columns if 'odds' in c.lower() or 'spread' in c.lower() or 'over' in c.lower()]
            if odds_cols:
                print(f"    {gf}: {odds_cols}")
                # Show sample data
                df_sample = pd.read_csv(filepath, nrows=5)
                for col in odds_cols:
                    non_null = df_sample[col].notna().sum()
                    print(f"      - {col}: {non_null}/5 rows have data")
        except Exception as e:
            print(f"    {gf}: Error reading - {e}")

# 4. Check if we have any betting line data at all
print("\n4. SUMMARY & RECOMMENDATIONS")
print("-"*80)

if odds_columns:
    print(f"  ✓ Database has {len(odds_columns)} odds-related columns")
    print("  → Strategy: ADD SUPPLEMENTAL columns from ESPN (don't overwrite)")
    print("  → Suggested new columns:")
    print("     - odds_espn_spread (ESPN's current spread)")
    print("     - odds_espn_total (ESPN's current total)")  
    print("     - odds_espn_moneyline_home")
    print("     - odds_espn_moneyline_away")
    print("     - odds_espn_provider (which sportsbook)")
    print("     - odds_espn_timestamp (when ESPN data was fetched)")
else:
    print("  ✗ No existing odds data in database")
    print("  → Strategy: ADD comprehensive odds columns")
    print("  → Suggested columns:")
    print("     - odds_spread")
    print("     - odds_total")
    print("     - odds_moneyline_home")
    print("     - odds_moneyline_away")
    print("     - odds_provider")
    print("     - odds_timestamp")

print("\n" + "="*80)
