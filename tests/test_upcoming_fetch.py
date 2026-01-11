#!/usr/bin/env python3
"""Quick test to see what the upcoming games fetchers return"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from utils.upcoming_games import fetch_espn_upcoming, fetch_nflcom_upcoming, fetch_db_upcoming, fetch_upcoming_with_source

print("=" * 80)
print("Testing ESPN upcoming...")
try:
    espn = fetch_espn_upcoming(days_ahead=7)
    print(f"ESPN returned {len(espn)} games:")
    for g in espn[:5]:  # First 5
        print(f"  {g}")
except Exception as e:
    print(f"ESPN error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Testing NFL.com upcoming...")
try:
    nfl = fetch_nflcom_upcoming(days_ahead=7)
    print(f"NFL.com returned {len(nfl)} games:")
    for g in nfl[:5]:
        print(f"  {g}")
except Exception as e:
    print(f"NFL.com error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Testing DB upcoming...")
try:
    db = fetch_db_upcoming()
    print(f"DB returned {len(db)} games:")
    for g in db[:5]:
        print(f"  {g}")
except Exception as e:
    print(f"DB error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Testing unified fetch_upcoming_with_source...")
try:
    games, source = fetch_upcoming_with_source(days_ahead=7)
    print(f"Source: {source}, Count: {len(games)}")
    for g in games[:5]:
        print(f"  {g}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
