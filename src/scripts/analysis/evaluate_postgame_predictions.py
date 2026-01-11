import sys
from pathlib import Path
import pandas as pd

# Ensure src on path
ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.pfr_scraper import PFRScraper
from models.archive.model_v2 import _TEAM_CODE_TO_NAME as CODE_TO_NAME

BOX_URLS = [
    "https://www.pro-football-reference.com/boxscores/202601100car.htm",
    "https://www.pro-football-reference.com/boxscores/202601100chi.htm",
]

OUT_DIR = ROOT / "outputs"
REPORTS_DIR = ROOT / "reports"
OUT_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

scraper = PFRScraper()

# Try to load postgame results from file first
postgame_path = OUT_DIR / "postgame_results_2026-01-10.csv"
results = []
if postgame_path.exists():
    try:
        postgame_df = pd.read_csv(postgame_path)
        # Convert to results list format
        for _, row in postgame_df.iterrows():
            results.append({
                'away_team': row.get('away_team'),
                'home_team': row.get('home_team'),
                'margin_home': row.get('margin_home'),
                'total_points': row.get('total_points')
            })
        print(f"Loaded {len(results)} postgame results from file")
    except Exception as e:
        print(f"Error loading postgame file: {e}")

# Fallback: Build actual results from season games index if file is empty
if not results:
    print("Fetching from PFR games index...")
    games_df = scraper.get_game_scores(2025)
    if games_df is not None and not games_df.empty:
        NAME_TO_CODE = {v: k for k, v in CODE_TO_NAME.items()}
        for col in ['winner','loser']:
            if col in games_df.columns:
                games_df[col] = games_df[col].map(NAME_TO_CODE).fillna(games_df[col])
        # Add totals
        games_df['pts_winner'] = pd.to_numeric(games_df.get('pts_winner'), errors='coerce')
        games_df['pts_loser'] = pd.to_numeric(games_df.get('pts_loser'), errors='coerce')
        games_df['total_points'] = games_df['pts_winner'] + games_df['pts_loser']
        pairs = [("LAR","CAR"), ("CHI","GNB")]
        for a,b in pairs:
            df_match = games_df[((games_df.get('winner') == a) & (games_df.get('loser') == b)) | ((games_df.get('winner') == b) & (games_df.get('loser') == a))]
            if df_match.empty:
                continue
            row = df_match.tail(1).iloc[0]
            w, l = row.get('winner'), row.get('loser')
            pw = row.get('pts_winner')
            pl = row.get('pts_loser')
            # Construct both orientations
            results.append({'away_team': a, 'home_team': b, 'margin_home': (pl - pw) if (b==w) else (pw - pl), 'total_points': pw + pl})
            results.append({'away_team': b, 'home_team': a, 'margin_home': (pw - pl) if (a==w) else (pl - pw), 'total_points': pw + pl})

# Save postgame results only if we fetched from PFR
if results and not postgame_path.exists():
    postgame_df = pd.DataFrame(results)
    postgame_df.to_csv(postgame_path, index=False)
    print(f"Saved postgame results to {postgame_path}")

# Load prior predictions
pred_files = [
    OUT_DIR / "predictions_rams_panthers_2026-01-10.csv",
    OUT_DIR / "predictions_v3_rams_panthers_2026-01-10.csv",
    OUT_DIR / "predictions_playoffs_week1_2026-01-10.csv",
]

predictions = []
for f in pred_files:
    if f.exists():
        try:
            df = pd.read_csv(f)
            df['source_file'] = f.name
            predictions.append(df)
        except Exception:
            pass

if not predictions:
    print("No prediction files found.")
else:
    preds_df = pd.concat(predictions, ignore_index=True)
    # Normalize columns we need
    # Expect columns: away_team, home_team, pred_margin_home, pred_total, model_version
    cols = preds_df.columns
    # Normalize team names to codes
    NAME_TO_CODE = {v: k for k, v in CODE_TO_NAME.items()}
    for col in ['home_team','away_team']:
        if col in preds_df.columns:
            preds_df[col] = preds_df[col].map(NAME_TO_CODE).fillna(preds_df[col])
    # Filter only the two matchups
    mask = (
        ((preds_df.get('home_team') == 'CAR') & (preds_df.get('away_team') == 'LAR')) |
        ((preds_df.get('home_team') == 'CHI') & (preds_df.get('away_team') == 'GNB')) |
        ((preds_df.get('home_team') == 'LAR') & (preds_df.get('away_team') == 'CAR')) |
        ((preds_df.get('home_team') == 'GNB') & (preds_df.get('away_team') == 'CHI'))
    )
    preds_df = preds_df[mask]

    # Join with actuals using team pair regardless of home/away order
    def match_key(df):
        a = df.get('away_team')
        h = df.get('home_team')
        return pd.Series({'key': df['away_team'] + '|' + df['home_team']})

    preds_df['key'] = preds_df['away_team'] + '|' + preds_df['home_team']
    actuals = []
    for r in results:
        k = f"{r.get('away_team')}|{r.get('home_team')}"
        actuals.append({'key': k, 'margin_home': r.get('margin_home'), 'total_points': r.get('total_points')})
    actuals_df = pd.DataFrame(actuals)
    # Fallback: if missing any, pull from season games index
    if actuals_df.empty or actuals_df['margin_home'].isna().any():
        games_df = scraper.get_game_scores(2025)
        # map names to codes for winner/loser
        if not games_df.empty:
            NAME_TO_CODE = {v: k for k, v in CODE_TO_NAME.items()}
            for col in ['winner','loser']:
                if col in games_df.columns:
                    games_df[col] = games_df[col].map(NAME_TO_CODE).fillna(games_df[col])
            # infer margin and total
            if 'pts_winner' in games_df.columns and 'pts_loser' in games_df.columns:
                games_df['total_points'] = pd.to_numeric(games_df['pts_winner'], errors='coerce') + pd.to_numeric(games_df['pts_loser'], errors='coerce')
            # add both orientations for matching
            extras = []
            pairs = [("LAR","CAR"), ("CHI","GNB")]
            for a,b in pairs:
                # winner/loser orientation
                df_match = games_df[((games_df.get('winner') == a) & (games_df.get('loser') == b)) | ((games_df.get('winner') == b) & (games_df.get('loser') == a))]
                if not df_match.empty:
                    row = df_match.tail(1).iloc[0]
                    w, l = row.get('winner'), row.get('loser')
                    pw = pd.to_numeric(row.get('pts_winner'), errors='coerce')
                    pl = pd.to_numeric(row.get('pts_loser'), errors='coerce')
                    # two orientations
                    extras.append({'key': f"{a}|{b}", 'margin_home': (pl - pw) if (b==w) else (pw - pl), 'total_points': (pw + pl)})
                    extras.append({'key': f"{b}|{a}", 'margin_home': (pw - pl) if (b==w) else (pl - pw), 'total_points': (pw + pl)})
            if extras:
                extra_df = pd.DataFrame(extras)
                actuals_df = pd.concat([actuals_df, extra_df], ignore_index=True)

    merged = preds_df.merge(actuals_df[['key','margin_home','total_points']], on='key', how='left')
    # Compute errors
    if 'pred_margin_home' in merged.columns:
        merged['abs_err_margin'] = (merged['pred_margin_home'] - merged['margin_home']).abs()
    if 'pred_total' in merged.columns:
        merged['abs_err_total'] = (merged['pred_total'] - merged['total_points']).abs()

    # Summaries
    summary = {
        'n_predictions': len(merged),
        'margin_MAE': float(merged['abs_err_margin'].mean()) if 'abs_err_margin' in merged.columns else None,
        'total_MAE': float(merged['abs_err_total'].mean()) if 'abs_err_total' in merged.columns else None,
    }
    print("Postgame evaluation summary:", summary)

    # Save merged evaluation
    eval_path = OUT_DIR / "postgame_eval_2026-01-10.csv"
    merged.to_csv(eval_path, index=False)
    print(f"Saved detailed evaluation to {eval_path}")

    # Write report
    report_path = REPORTS_DIR / "POSTGAME_EVAL_2026-01-10.md"
    with report_path.open('w', encoding='utf-8') as f:
        f.write("# Postgame Evaluation (2026-01-10)\n\n")
        f.write(f"Games scraped: {len(results)}\n\n")
        f.write(f"Margin MAE: {summary['margin_MAE']}\n\n")
        f.write(f"Total MAE: {summary['total_MAE']}\n\n")
        f.write("## Details\n\n")
        cols_to_show = ['source_file','model_version','away_team','home_team','pred_margin_home','margin_home','abs_err_margin','pred_total','total_points','abs_err_total']
        present = [c for c in cols_to_show if c in merged.columns]
        # Fallback to CSV-style markdown if tabulate not installed
        try:
            f.write(merged[present].to_markdown(index=False))
        except Exception:
            f.write('\n')
            f.write(','.join(present) + '\n')
            for _, row in merged[present].iterrows():
                f.write(','.join(str(row[c]) for c in present) + '\n')
    print(f"Wrote report to {report_path}")
