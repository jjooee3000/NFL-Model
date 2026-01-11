import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))
from utils.pfr_scraper import PFRScraper

urls = [
    'https://www.pro-football-reference.com/boxscores/202601100car.htm',
    'https://www.pro-football-reference.com/boxscores/202601100chi.htm',
]

s = PFRScraper()
for u in urls:
    print('Parsing:', u)
    print(s.get_boxscore_basic(u))
