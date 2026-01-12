"""
Run HOU@PIT Playoff Prediction - January 12, 2026

Uses enhanced model with:
- 6.5x more training data (3,592 team_games vs 546)
- 99% rest days coverage
- Weather data infrastructure
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import sqlite3
import pandas as pd
from datetime import datetime
from models.model_v3 import NFLHybridModelV3
from utils.paths import DATA_DIR

def main():
    print("=" * 80)
    print("HOU @ PIT PLAYOFF PREDICTION - Wild Card Round")
    print("January 12, 2026")
    print("=" * 80)
    print("\nModel Enhancements:")
    print("  - Training data: 3,592 team_games (6.5x more than before)")
    print("  - Rest days: 99% populated")
    print("  - Weather: Infrastructure ready")
    print("=" * 80)
    
    # Initialize model with SQLite database
    db_path = DATA_DIR / "nfl_model.db"
    print(f"\nLoading model from: {db_path}")
    
    model = NFLHybridModelV3(
        workbook_path=str(db_path),  # Pass DB path as workbook_path
        model_type="randomforest",
        window=8,
        prefer_sqlite=True  # Use SQLite instead of Excel
    )
    
    # Train model through week 18 (regular season)
    print("\nTraining model through Week 18...")
    report = model.fit(train_through_week=18)
    
    print(f"\nTraining Results:")
    print(f"  - Games trained: {report['n_train_games']}")
    print(f"  - Features used: {report['n_features']}")
    print(f"  - Test games: {report['n_test_games']}")
    if report['margin_MAE_test']:
        print(f"  - Margin MAE (test): {report['margin_MAE_test']:.2f} pts")
        print(f"  - Total MAE (test): {report['total_MAE_test']:.2f} pts")
    print(f"  - Model type: {report['model_type']}")
    
    # Get HOU@PIT game info
    print("\n" + "=" * 80)
    print("GAME INFORMATION")
    print("=" * 80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get game details
    cursor.execute("""
        SELECT game_id, away_team, home_team, week, 
               "game_date_yyyy-mm-dd", kickoff_time_local, stadium,
               home_rest_days, away_rest_days,
               temp_f, wind_mph, precip_inch, is_indoor
        FROM games
        WHERE game_id = '2025_W19_HOU_PIT'
    """)
    game_info = cursor.fetchone()
    
    if not game_info:
        print("ERROR: HOU@PIT game not found in database")
        conn.close()
        return
    
    (game_id, away_team, home_team, week, game_date, kickoff_time, stadium,
     home_rest, away_rest, temp, wind, precip, is_indoor) = game_info
    
    print(f"Game ID: {game_id}")
    print(f"Matchup: {away_team} @ {home_team}")
    print(f"Date: {game_date}")
    print(f"Kickoff: {kickoff_time}")
    print(f"Stadium: {stadium}")
    print(f"Rest Days: HOU {away_rest if away_rest else 'N/A'}, PIT {home_rest if home_rest else 'N/A'}")
    if is_indoor:
        print(f"Venue: Indoor")
    else:
        print(f"Weather: {temp}°F, {wind} mph wind, {precip}\" precip" if temp else "Weather: TBD")
    
    # Get odds if available
    cursor.execute("""
        SELECT close_spread_home, close_total, close_ml_home, close_ml_away
        FROM odds
        WHERE game_id = '2025_W19_HOU_PIT'
    """)
    odds_data = cursor.fetchone()
    
    if odds_data and odds_data[0]:
        spread, total, ml_home, ml_away = odds_data
        print(f"\nVegas Line:")
        print(f"  Spread: PIT {spread:+.1f}")
        print(f"  Total: {total:.1f}")
        print(f"  Moneyline: PIT {ml_home}, HOU {ml_away}")
    else:
        spread, total, ml_home, ml_away = None, None, None, None
        print(f"\nVegas Line: Not available")
    
    conn.close()
    
    # Run prediction
    print("\n" + "=" * 80)
    print("MODEL PREDICTION")
    print("=" * 80)
    
    try:
        prediction = model.predict_game(
            away_team=away_team,
            home_team=home_team,
            week=int(week),
            close_spread_home=spread,
            close_total=total,
            close_ml_home=ml_home,
            close_ml_away=ml_away
        )
        
        # Extract predictions
        pred_margin = prediction['predicted_margin_home']
        pred_total = prediction['predicted_total']
        pred_home_score = (pred_total + pred_margin) / 2
        pred_away_score = (pred_total - pred_margin) / 2
        win_prob_home = prediction.get('win_prob_home', 0.5)
        
        # Determine winner
        if pred_margin > 0:
            winner = home_team
            spread_pick = f"{home_team} -{abs(pred_margin):.1f}"
            confidence = win_prob_home * 100
        else:
            winner = away_team
            spread_pick = f"{away_team} -{abs(pred_margin):.1f}"
            confidence = (1 - win_prob_home) * 100
        
        # Over/Under
        if total:
            ou_diff = pred_total - total
            if ou_diff > 0:
                ou_pick = f"OVER {total:.1f}"
            else:
                ou_pick = f"UNDER {total:.1f}"
        else:
            ou_pick = f"Projected Total: {pred_total:.1f}"
        
        print(f"\nPREDICTED WINNER: {winner} ({confidence:.1f}% confidence)")
        print(f"\nPredicted Score:")
        print(f"  {away_team}: {pred_away_score:.1f}")
        print(f"  {home_team}: {pred_home_score:.1f}")
        print(f"  Margin: {home_team} {pred_margin:+.1f}")
        
        print(f"\nBetting Recommendations:")
        print(f"  Spread: {spread_pick}")
        print(f"  Over/Under: {ou_pick}")
        
        if spread:
            diff_from_vegas = pred_margin - spread
            print(f"\nModel vs Vegas:")
            print(f"  Model spread: {home_team} {pred_margin:+.1f}")
            print(f"  Vegas spread: {home_team} {spread:+.1f}")
            print(f"  Edge: {abs(diff_from_vegas):.1f} pts {'for ' + home_team if diff_from_vegas > 0 else 'for ' + away_team}")
        
        # Save prediction to database
        print("\n" + "=" * 80)
        print("SAVING PREDICTION")
        print("=" * 80)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Save to predictions table
        timestamp = datetime.now().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO predictions 
            (game_id, timestamp, model_version, away_team, home_team, 
             pred_away_score, pred_home_score, pred_margin_home, pred_total,
             pred_winner, win_prob_home, train_through_week)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (game_id, timestamp, 'v3_enhanced', away_team, home_team,
              pred_away_score, pred_home_score, pred_margin, pred_total,
              winner, win_prob_home, 18))
        
        conn.commit()
        conn.close()
        
        print(f"Prediction saved to database")
        print(f"Timestamp: {timestamp}")
        
        print("\n" + "=" * 80)
        print("PREDICTION COMPLETE")
        print("=" * 80)
        print(f"\nSummary:")
        print(f"  Winner: {winner}")
        print(f"  Score: {away_team} {pred_away_score:.1f}, {home_team} {pred_home_score:.1f}")
        print(f"  Spread: {spread_pick}")
        print(f"  Total: {ou_pick}")
        print("=" * 80)
        
        # Return prediction data for use by homepage
        return {
            'game_id': game_id,
            'away_team': away_team,
            'home_team': home_team,
            'winner': winner,
            'pred_away_score': pred_away_score,
            'pred_home_score': pred_home_score,
            'pred_margin': pred_margin,
            'pred_total': pred_total,
            'spread_pick': spread_pick,
            'ou_pick': ou_pick,
            'confidence': confidence,
            'timestamp': timestamp
        }
        
    except Exception as e:
        print(f"\nERROR during prediction: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = main()
    if result:
        print(f"\nPrediction data returned successfully")
    else:
        print(f"\nPrediction failed")
        sys.exit(1)
