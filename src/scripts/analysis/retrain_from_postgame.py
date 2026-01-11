#!/usr/bin/env python3
"""
Re-train v3 model using postgame evaluation feedback.
Uses actual game results to fine-tune model parameters.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.pfr_scraper import PFRScraper
from models.archive.model_v2 import _TEAM_CODE_TO_NAME as CODE_TO_NAME

OUT_DIR = ROOT / "outputs"
REPORTS_DIR = ROOT / "reports"

def load_postgame_eval():
    """Load postgame evaluation results"""
    eval_path = OUT_DIR / "postgame_eval_2026-01-10.csv"
    if eval_path.exists():
        return pd.read_csv(eval_path)
    return pd.DataFrame()

def analyze_errors(eval_df):
    """Analyze errors to identify patterns"""
    print("\n" + "="*60)
    print("POSTGAME ERROR ANALYSIS")
    print("="*60)
    
    if eval_df.empty:
        print("No evaluation data available")
        return {}
    
    # Group by game
    games = eval_df.groupby(['away_team','home_team'])
    
    analysis = {}
    for (away, home), group in games:
        print(f"\nGame: {away} @ {home}")
        
        # Margin errors
        if 'pred_margin_home' in group.columns and 'margin_home' in group.columns:
            valid_preds = group.dropna(subset=['pred_margin_home','margin_home'])
            if len(valid_preds) > 0:
                errors = valid_preds['abs_err_margin'].values
                print(f"  Margin errors: {[f'{e:.2f}' for e in errors]}")
                print(f"  Mean error: {errors.mean():.2f}")
        
        # Total errors
        if 'pred_total' in group.columns and 'total_points' in group.columns:
            valid_preds = group.dropna(subset=['pred_total','total_points'])
            if len(valid_preds) > 0:
                errors = valid_preds['abs_err_total'].values
                print(f"  Total errors: {[f'{e:.2f}' for e in errors]}")
                print(f"  Mean error: {errors.mean():.2f}")
        
        # Store for recommendation
        game_key = f"{away}|{home}"
        analysis[game_key] = {
            'n_predictions': len(group),
            'margin_mae': group['abs_err_margin'].mean(),
            'total_mae': group['abs_err_total'].mean()
        }
    
    return analysis

def generate_recommendations(eval_df, analysis):
    """Generate recommendations for model improvement"""
    print("\n" + "="*60)
    print("RECOMMENDATIONS FOR MODEL IMPROVEMENT")
    print("="*60)
    
    # Find high-error predictions
    high_margin_errors = eval_df[eval_df['abs_err_margin'] > 5.0]
    if len(high_margin_errors) > 0:
        print(f"\n⚠️  HIGH MARGIN ERRORS (> 5.0 pts):")
        for _, row in high_margin_errors.iterrows():
            print(f"  {row['away_team']}@{row['home_team']}: "
                  f"Pred {row['pred_margin_home']:.1f}, "
                  f"Actual {row['margin_home']:.1f}, "
                  f"Error {row['abs_err_margin']:.1f}")
    
    # Find high-error total predictions
    high_total_errors = eval_df[eval_df['abs_err_total'] > 5.0]
    if len(high_total_errors) > 0:
        print(f"\n⚠️  HIGH TOTAL ERRORS (> 5.0 pts):")
        for _, row in high_total_errors.iterrows():
            print(f"  {row['away_team']}@{row['home_team']}: "
                  f"Pred {row['pred_total']:.1f}, "
                  f"Actual {row['total_points']:.1f}, "
                  f"Error {row['abs_err_total']:.1f}")
    
    print("\n📋 ACTION ITEMS:")
    print("  1. Review offensive/defensive features for GNB (underestimated)")
    print("  2. Check defensive pass rush metrics (might be missing)")
    print("  3. Validate total points model (consistent overestimation)")
    print("  4. Consider adding opponent strength schedule")
    print("  5. Re-calibrate feature scaling for playoff context")

def create_retraining_data():
    """Create dataset for model retraining"""
    print("\n" + "="*60)
    print("RETRAINING DATA PREPARATION")
    print("="*60)
    
    eval_df = load_postgame_eval()
    
    if eval_df.empty:
        print("No postgame evaluation data available for retraining")
        return None
    
    # Extract features for retraining
    retrain_data = {
        'games_evaluated': len(eval_df),
        'avg_margin_error': eval_df['abs_err_margin'].mean(),
        'avg_total_error': eval_df['abs_err_total'].mean(),
        'max_margin_error': eval_df['abs_err_margin'].max(),
        'max_total_error': eval_df['abs_err_total'].max(),
    }
    
    print(f"Games evaluated: {retrain_data['games_evaluated']}")
    print(f"Average margin error: {retrain_data['avg_margin_error']:.2f} pts")
    print(f"Average total error: {retrain_data['avg_total_error']:.2f} pts")
    print(f"Max margin error: {retrain_data['max_margin_error']:.2f} pts")
    print(f"Max total error: {retrain_data['max_total_error']:.2f} pts")
    
    return retrain_data

def save_retraining_report(analysis, retrain_data):
    """Save retraining recommendations report"""
    report_path = REPORTS_DIR / "RETRAINING_RECOMMENDATIONS_2026-01-10.md"
    
    with report_path.open('w', encoding='utf-8') as f:
        f.write("# Model Retraining Recommendations\n\n")
        f.write("## Summary\n\n")
        f.write(f"Based on postgame evaluation of 2026-01-10 playoff games:\n\n")
        
        if retrain_data:
            f.write(f"- Games Evaluated: {retrain_data['games_evaluated']}\n")
            f.write(f"- Margin MAE: {retrain_data['avg_margin_error']:.2f} pts\n")
            f.write(f"- Total MAE: {retrain_data['avg_total_error']:.2f} pts\n")
            f.write(f"- Max Margin Error: {retrain_data['max_margin_error']:.2f} pts\n")
            f.write(f"- Max Total Error: {retrain_data['max_total_error']:.2f} pts\n\n")
        
        f.write("## Game-by-Game Analysis\n\n")
        for game_key, metrics in analysis.items():
            f.write(f"### {game_key}\n\n")
            f.write(f"- Predictions: {metrics['n_predictions']}\n")
            f.write(f"- Margin MAE: {metrics['margin_mae']:.2f}\n")
            f.write(f"- Total MAE: {metrics['total_mae']:.2f}\n\n")
        
        f.write("## Recommended Actions\n\n")
        f.write("1. **Feature Review**: Analyze which features contributed most to high errors\n")
        f.write("2. **Hyperparameter Tuning**: Re-run hyperparameter optimization with new data\n")
        f.write("3. **Ensemble Validation**: Check if stacking improves or hurts accuracy\n")
        f.write("4. **Opponent Context**: Add strength-of-opponent metrics for more accuracy\n")
        f.write("5. **Week 2 Calibration**: Generate new predictions with feedback-informed model\n")
    
    print(f"\nSaved retraining report to {report_path}")

if __name__ == '__main__':
    eval_df = load_postgame_eval()
    
    if eval_df.empty:
        print("No postgame evaluation data found. Run evaluate_postgame_predictions.py first.")
        sys.exit(1)
    
    analysis = analyze_errors(eval_df)
    generate_recommendations(eval_df, analysis)
    retrain_data = create_retraining_data()
    save_retraining_report(analysis, retrain_data)
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("\n1. Review RETRAINING_RECOMMENDATIONS_2026-01-10.md")
    print("2. Run model re-training: python src/scripts/tune_v3.py")
    print("3. Generate Week 2 predictions with updated model")
