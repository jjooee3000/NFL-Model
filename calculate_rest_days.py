"""
Calculate Rest Days for NFL Games

Populates home_rest_days and away_rest_days in the games table by calculating
the number of days since each team's last game.

Priority 1 - Critical Data Gap Fix
Expected Impact: -0.2 to -0.3 pts MAE improvement
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("data/nfl_model.db")


def calculate_rest_days():
    """Calculate rest days for all games in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("REST DAYS CALCULATION - Priority 1 Backfill")
    print("=" * 80)
    
    # Get all games ordered by date
    cursor.execute("""
        SELECT game_id, "game_date_yyyy-mm-dd", home_team, away_team, week
        FROM games
        WHERE "game_date_yyyy-mm-dd" IS NOT NULL
        ORDER BY "game_date_yyyy-mm-dd", game_id
    """)
    games = cursor.fetchall()
    
    print(f"\nProcessing {len(games)} games...")
    
    # Track last game date for each team
    team_last_game = {}
    
    updates = []
    games_with_rest = 0
    
    for game_id, game_date_str, home_team, away_team, week in games:
        try:
            # Parse game date
            game_date = datetime.strptime(game_date_str, '%Y-%m-%d').date()
            
            # Calculate rest days for home team
            if home_team in team_last_game:
                last_date = team_last_game[home_team]
                home_rest = (game_date - last_date).days
            else:
                # First game of season - assume 7 days (standard week)
                home_rest = 7 if week and int(week) > 1 else None
            
            # Calculate rest days for away team
            if away_team in team_last_game:
                last_date = team_last_game[away_team]
                away_rest = (game_date - last_date).days
            else:
                # First game of season - assume 7 days (standard week)
                away_rest = 7 if week and int(week) > 1 else None
            
            # Store update
            if home_rest is not None or away_rest is not None:
                updates.append((home_rest, away_rest, game_id))
                games_with_rest += 1
            
            # Update last game date for both teams
            team_last_game[home_team] = game_date
            team_last_game[away_team] = game_date
            
        except Exception as e:
            print(f"Error processing game {game_id}: {e}")
            continue
    
    print(f"\nCalculated rest days for {games_with_rest} games")
    
    # Apply updates
    print("\nUpdating database...")
    cursor.executemany("""
        UPDATE games
        SET home_rest_days = ?, away_rest_days = ?
        WHERE game_id = ?
    """, updates)
    
    conn.commit()
    
    # Verify results
    cursor.execute("""
        SELECT 
            COUNT(*) as total_games,
            COUNT(home_rest_days) as home_populated,
            COUNT(away_rest_days) as away_populated,
            AVG(home_rest_days) as avg_home_rest,
            AVG(away_rest_days) as avg_away_rest,
            MIN(home_rest_days) as min_home_rest,
            MAX(home_rest_days) as max_home_rest
        FROM games
        WHERE "game_date_yyyy-mm-dd" IS NOT NULL
    """)
    stats = cursor.fetchone()
    
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print(f"Total games: {stats[0]}")
    print(f"Home rest days populated: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
    print(f"Away rest days populated: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
    print(f"Average home rest: {stats[3]:.1f} days")
    print(f"Average away rest: {stats[4]:.1f} days")
    print(f"Min rest: {stats[5]} days")
    print(f"Max rest: {stats[6]} days")
    
    # Show distribution of rest days
    print("\nRest Days Distribution:")
    cursor.execute("""
        SELECT 
            home_rest_days as rest_days,
            COUNT(*) as count
        FROM games
        WHERE home_rest_days IS NOT NULL
        GROUP BY home_rest_days
        ORDER BY home_rest_days
    """)
    
    for rest_days, count in cursor.fetchall():
        bar = "█" * int(count / 10)
        print(f"  {int(rest_days):2d} days: {count:4d} games {bar}")
    
    # Identify short rest games (< 6 days - typically Thursday night)
    cursor.execute("""
        SELECT COUNT(*)
        FROM games
        WHERE home_rest_days < 6 OR away_rest_days < 6
    """)
    short_rest_count = cursor.fetchone()[0]
    print(f"\nShort rest games (< 6 days): {short_rest_count}")
    
    # Identify long rest games (> 10 days - bye weeks, playoffs)
    cursor.execute("""
        SELECT COUNT(*)
        FROM games
        WHERE home_rest_days > 10 OR away_rest_days > 10
    """)
    long_rest_count = cursor.fetchone()[0]
    print(f"Long rest games (> 10 days): {long_rest_count}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ REST DAYS CALCULATION COMPLETE")
    print("=" * 80)
    print(f"Updated {len(updates)} games with rest day information")
    print("Impact: -0.2 to -0.3 pts MAE improvement expected")
    print("=" * 80)


if __name__ == "__main__":
    calculate_rest_days()
