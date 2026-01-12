"""Verify the enriched data was populated correctly"""
import sqlite3

conn = sqlite3.connect('data/nfl_model.db')

print("="*80)
print("PHASE 1 ENRICHMENT - VERIFICATION")
print("="*80)

# Check which games have odds data
print("\n1. GAMES WITH ODDS DATA")
print("-"*80)
result = conn.execute("""
    SELECT 
        game_id, away_team, home_team,
        odds_spread, odds_total, 
        odds_moneyline_home, odds_moneyline_away,
        odds_provider
    FROM games
    WHERE odds_spread IS NOT NULL
    ORDER BY game_id DESC
    LIMIT 10
""").fetchall()

if result:
    for row in result:
        game_id, away, home, spread, total, ml_home, ml_away, provider = row
        print(f"\n{game_id}: {away}@{home}")
        print(f"  Spread: {spread} | Total: {total}")
        print(f"  Moneyline: Home {ml_home}, Away {ml_away}")
        print(f"  Provider: {provider}")
else:
    print("  ✗ No odds data found")

# Check team records
print("\n2. GAMES WITH TEAM RECORDS")
print("-"*80)
result = conn.execute("""
    SELECT 
        game_id, away_team, home_team,
        home_record_wins, home_record_losses,
        away_record_wins, away_record_losses
    FROM games
    WHERE home_record_wins IS NOT NULL
    ORDER BY game_id DESC
    LIMIT 5
""").fetchall()

if result:
    for row in result:
        game_id, away, home, hw, hl, aw, al = row
        print(f"{game_id}: {away}@{home}")
        print(f"  {home} record: {hw}-{hl} | {away} record: {aw}-{al}")
else:
    print("  ✗ No team records found")

# Check attendance
print("\n3. GAMES WITH ATTENDANCE DATA")
print("-"*80)
result = conn.execute("""
    SELECT 
        game_id, away_team, home_team,
        attendance, broadcast_network
    FROM games
    WHERE attendance > 0
    ORDER BY game_id DESC
    LIMIT 5
""").fetchall()

if result:
    for row in result:
        game_id, away, home, attend, broadcast = row
        print(f"{game_id}: {away}@{home}")
        print(f"  Attendance: {attend:,} | Network: {broadcast}")
else:
    print("  ✗ No attendance data found")

# Summary statistics
print("\n4. SUMMARY STATISTICS")
print("-"*80)
stats = conn.execute("""
    SELECT 
        COUNT(*) as total_games,
        SUM(CASE WHEN odds_spread IS NOT NULL THEN 1 ELSE 0 END) as with_odds,
        SUM(CASE WHEN home_record_wins IS NOT NULL THEN 1 ELSE 0 END) as with_records,
        SUM(CASE WHEN attendance > 0 THEN 1 ELSE 0 END) as with_attendance,
        SUM(CASE WHEN broadcast_network IS NOT NULL THEN 1 ELSE 0 END) as with_broadcast
    FROM games
""").fetchone()

total, odds, records, attendance, broadcast = stats
print(f"Total games: {total}")
print(f"Games with odds: {odds} ({odds/total*100:.1f}%)")
print(f"Games with team records: {records} ({records/total*100:.1f}%)")
print(f"Games with attendance: {attendance} ({attendance/total*100:.1f}%)")
print(f"Games with broadcast info: {broadcast} ({broadcast/total*100:.1f}%)")

conn.close()

print("\n" + "="*80)
