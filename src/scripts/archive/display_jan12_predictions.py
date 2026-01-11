# Archived: display_jan12_predictions.py
# Replacement: Use the API (/predictions/{game_id}) or POST /predict, and daily pipeline outputs.
# See: src/nfl_model/services/api/app.py and src/scripts/predict_ensemble_multiwindow.py

import pandas as pd

# Original functionality retained for reference

df = pd.read_csv('outputs/prediction_log.csv')
latest_time = df[df['game_id'].isin(['2025_01_BUF_JAX', '2025_01_SFO_PHI', '2025_01_LAC_NWE'])]['timestamp'].max()
recent = df[(df['timestamp'] == latest_time) & (df['game_id'].isin(['2025_01_BUF_JAX', '2025_01_SFO_PHI', '2025_01_LAC_NWE']))]

print('\n' + '='*80)
print('PLAYOFF PREDICTIONS FOR JANUARY 12, 2026 (WITH FULL SQLite DATA)')
print('='*80 + '\n')

for _, row in recent.iterrows():
    away = row['away_team']
    home = row['home_team']
    margin = row['pred_margin_home']
    total = row['pred_total']
    win_prob_home = row['pred_winprob_home'] * 100

    print(f'{away:6} @ {home:6}')
    print(f'  Spread: {abs(margin):5.1f} pts ({home if margin > 0 else away} favored)')
    print(f'  Total:  {total:5.1f} pts')
    print(f'  Home Win Probability: {win_prob_home:5.1f}%')
    print()
