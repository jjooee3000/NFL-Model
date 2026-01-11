import sqlite3
from pathlib import Path
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / 'data' / 'nfl_model.db'
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils.db_dedupe import to_sql_dedup_append

def main():
    df = pd.DataFrame([
        {
            'boxscore_stats_link': 'https://www.pro-football-reference.com/boxscores/202501010buf.htm',
            'season': 2025,
            'week': 1,
            'tm_alias': 'BUF',
            'opp_alias': 'JAX',
            'tm_location': 'H',
            'opp_location': 'A',
            'event_date': '2025-01-01'
        },
        {
            'boxscore_stats_link': 'https://www.pro-football-reference.com/boxscores/202501010buf.htm',
            'season': 2025,
            'week': 1,
            'tm_alias': 'BUF',
            'opp_alias': 'JAX',
            'tm_location': 'H',
            'opp_location': 'A',
            'event_date': '2025-01-01'
        }
    ])
    with sqlite3.connect(str(DB_PATH)) as conn:
        before = pd.read_sql_query("SELECT COUNT(*) AS c FROM pfr_seasons WHERE boxscore_stats_link = ?", conn, params=('https://www.pro-football-reference.com/boxscores/202501010buf.htm',))
        print("Before:", int(before['c'].iloc[0]))
        written = to_sql_dedup_append(conn, df, 'pfr_seasons')
        print("Written:", written)
        after = pd.read_sql_query("SELECT COUNT(*) AS c FROM pfr_seasons WHERE boxscore_stats_link = ?", conn, params=('https://www.pro-football-reference.com/boxscores/202501010buf.htm',))
        print("After:", int(after['c'].iloc[0]))

if __name__ == '__main__':
    main()
