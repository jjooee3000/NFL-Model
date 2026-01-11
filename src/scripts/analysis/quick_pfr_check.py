import sys
from pathlib import Path

# Ensure src is on path
ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.pfr_scraper import PFRScraper
import pandas as pd
from models.archive.model_v2 import _TEAM_CODE_TO_NAME as CODE_TO_NAME

TEAMS = ["LAR", "CAR", "CHI", "GNB"]
SEASON = 2025

scraper = PFRScraper()

print("\n=== Checking latest game logs and boxscores ===")
print(f"Teams: {', '.join(TEAMS)} | Season: {SEASON}")

# Fetch season games once
games_df = scraper.get_game_scores(SEASON)
if not games_df.empty:
    # Normalize winner/loser to our team codes using names mapping
    NAME_TO_CODE = {v: k for k, v in CODE_TO_NAME.items()}
    for col in ['winner', 'loser']:
        if col in games_df.columns:
            games_df[col] = games_df[col].map(NAME_TO_CODE).fillna(games_df[col])

def find_match_boxscore(team_a: str, team_b: str) -> str:
    if games_df.empty:
        return None
    mask = (
        (games_df.get('winner','') == team_a) & (games_df.get('loser','') == team_b)
    ) | (
        (games_df.get('winner','') == team_b) & (games_df.get('loser','') == team_a)
    )
    df = games_df[mask]
    if df.empty:
        return None
    return df.tail(1).iloc[0].get('boxscore_url')

pairs = [("LAR","CAR"), ("CHI","GNB")]
for a,b in pairs:
    url = find_match_boxscore(a,b)
    print(f"- {a} vs {b}: boxscore_url = {url}")

print("\n=== Latest team log entries ===")
for team in TEAMS:
    log = scraper.get_team_game_log(team, SEASON)
    if log.empty:
        print(f"- {team}: No game log data found")
        continue
    # Filter to rows with a result or boxscore	note
    df = log.copy()
    if 'result' in df.columns:
        df = df[df['result'].astype(str).str.len() > 0]
    if df.empty:
        last = log.tail(1)
    else:
        last = df.tail(1)
    rec = last.to_dict('records')[0]
    opp = rec.get('opp', '')
    result = rec.get('result', '')
    box = rec.get('boxscore_word', '')
    print(f"- {team} vs {opp}: {result} | box: {box}")
