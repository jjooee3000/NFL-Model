#!/usr/bin/env python3
"""
Manual postgame data entry script.
Use this to enter final scores for completed games.
"""
import pandas as pd
import json
from pathlib import Path

def get_game_scores_interactive():
    """Interactively collect game scores from user"""
    print("=" * 60)
    print("POSTGAME SCORE ENTRY")
    print("=" * 60)
    print("\nEnter final scores for completed playoff games (2026-01-10)")
    print("Format: away_team,home_team,away_score,home_score")
    print("\nGames to enter:")
    print("1. Rams @ Panthers (LAR @ CAR)")
    print("2. Bears @ Packers (CHI @ GNB)")
    print("\nEnter 'done' when finished.\n")
    
    games = []
    game_count = 0
    
    while True:
        game_count += 1
        print(f"\nGame {game_count}:")
        away = input("Away team (e.g., LAR): ").strip().upper()
        if away.lower() == 'done':
            break
        
        home = input("Home team (e.g., CAR): ").strip().upper()
        away_score = input(f"{away} score: ").strip()
        home_score = input(f"{home} score: ").strip()
        
        try:
            games.append({
                'away_team': away,
                'home_team': home,
                'away_score': int(away_score),
                'home_score': int(home_score),
                'date': '2026-01-10'
            })
            print(f"✓ Recorded: {away} {away_score}, {home} {home_score}")
        except ValueError:
            print("✗ Invalid score format. Please use integers.")
            continue
    
    return pd.DataFrame(games)

def save_postgame_results(df, output_file='postgame_results_2026-01-10.csv'):
    """Save postgame results to CSV"""
    output_path = Path(__file__).parent.parent.parent.parent / 'outputs' / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(output_path, index=False)
    print(f"\n✓ Saved to {output_path}")
    return output_path

def create_sample_data():
    """Create sample postgame data for testing"""
    # Rams 27, Panthers 24 -> margin_home (CAR) = -3 (away Rams won)
    # Bears 24, Packers 28 -> margin_home (GNB) = 4 (home Packers won)
    sample_data = {
        'away_team': ['LAR', 'CHI'],
        'home_team': ['CAR', 'GNB'],
        'margin_home': [-3, 4],  # home_score - away_score
        'total_points': [51, 52],  # 27+24=51, 24+28=52
        'date': ['2026-01-10', '2026-01-10']
    }
    return pd.DataFrame(sample_data)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--sample':
        print("Creating sample postgame data for testing...")
        df = create_sample_data()
        save_postgame_results(df)
        print("\nSample data:")
        print(df)
    else:
        df = get_game_scores_interactive()
        if len(df) > 0:
            save_postgame_results(df)
            print("\nEntered games:")
            print(df)
        else:
            print("\nNo games entered.")
