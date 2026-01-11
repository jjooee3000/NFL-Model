"""
Mark upcoming games (by week) as prediction targets in the workbook.

Usage:
  python src/scripts/set_prediction_targets.py --workbook data/nfl_2025_model_data_with_moneylines.xlsx --week 19
"""
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description='Mark upcoming games as prediction targets')
    parser.add_argument('--workbook', type=str, required=True)
    parser.add_argument('--week', type=int, required=True)
    args = parser.parse_args()

    wb_path = Path(args.workbook)
    if not wb_path.exists():
        print(f'Workbook not found: {wb_path}')
        return

    games = pd.read_excel(wb_path, sheet_name='games')

    # Ensure column exists
    if 'is_prediction_target' not in games.columns:
        games['is_prediction_target'] = 0

    # Mark week matches (ignore date filters if scheduling isn't finalized)
    mask = (games['week'] == args.week)
    games.loc[mask, 'is_prediction_target'] = 1

    # Write back
    with pd.ExcelWriter(wb_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        games.to_excel(writer, sheet_name='games', index=False)

    marked = games.loc[mask, ['game_id', 'away_team', 'home_team', 'week']]
    print(f'Marked {len(marked)} game(s) for week {args.week} as prediction targets:')
    if not marked.empty:
        print(marked.to_string(index=False))


if __name__ == '__main__':
    main()
