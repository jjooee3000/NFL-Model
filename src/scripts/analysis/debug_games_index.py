import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))
from utils.pfr_scraper import PFRScraper
from models.archive.model_v2 import _TEAM_CODE_TO_NAME as CODE_TO_NAME
import pandas as pd

s = PFRScraper()
df = s.get_game_scores(2025)
print('Columns:', list(df.columns))
NAME_TO_CODE = {v: k for k, v in CODE_TO_NAME.items()}
for col in ['winner','loser']:
    if col in df.columns:
        df[col] = df[col].map(NAME_TO_CODE).fillna(df[col])
print(df.tail(10))
mask = ((df.get('winner')=='LAR') & (df.get('loser')=='CAR')) | ((df.get('winner')=='CAR') & (df.get('loser')=='LAR'))
print('LAR/CAR matches:', df[mask])
mask2 = ((df.get('winner')=='CHI') & (df.get('loser')=='GNB')) | ((df.get('winner')=='GNB') & (df.get('loser')=='CHI'))
print('CHI/GNB matches:', df[mask2])
