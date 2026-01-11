"""
Migrate NFL model data (Excel + CSVs) into a SQLite database.

Inputs:
- Excel: data/nfl_2025_model_data_with_moneylines.xlsx (primary workbook)
- Excel: data/nfl_model_data_historical_integrated.xlsx (merged historical + 2025)
- CSVs: data/pfr_historical/* (PFR scraped outputs)

Output:
- SQLite DB: data/nfl_model.db

Tables:
- games (2020-2025 merged)
- team_games, odds, injuries_qb, passing, defense_team_games, offense_team_games,
  odds_team_games, rushing_team_games, penalties_team_games, defense_drives_team_games,
  punting_team_games, opening_odds_source, moneylines_source (from 2025 workbook)
- pfr_team_stats, pfr_team_defense, pfr_games, pfr_team_gamelogs
- pfr_advanced_passing, pfr_advanced_rushing, pfr_advanced_receiving, pfr_advanced_defense
- pfr_situational_conversions, pfr_situational_drives, pfr_situational_scoring

Indexes:
- games(game_id), games(season), games(week), games(home_team), games(away_team)
- team_games(game_id), team_games(team), team_games(week)
- odds(game_id)
- pfr_* tables: (season), (team) where applicable
"""

from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data'
DB_PATH = DATA / 'nfl_model.db'
WB_2025 = DATA / 'nfl_2025_model_data_with_moneylines.xlsx'
WB_HIST = DATA / 'nfl_model_data_historical_integrated.xlsx'
PFR_DIR = DATA / 'pfr_historical'

# Sheet names from 2025 workbook
WB_SHEETS_2025 = [
    'games', 'injuries_qb', 'passing', 'defense_team_games', 'offense_team_games', 'odds_team_games',
    'rushing_team_games', 'penalties_team_games', 'opening_odds_source', 'defense_drives_team_games',
    'punting_team_games', 'team_games', 'odds', 'moneylines_source'
]

# Historical sheets
WB_HIST_SHEETS = [
    'games', 'pfr_team_stats_historical', 'pfr_advanced_passing', 'pfr_advanced_rushing',
    'pfr_advanced_receiving', 'pfr_advanced_defense'
]


def write_table(conn: sqlite3.Connection, name: str, df: pd.DataFrame) -> None:
    logger.info(f"Writing table: {name} ({len(df)} rows)")
    # Normalize column names to snake_case-like
    df = df.copy()
    df.columns = [c.strip().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').lower() for c in df.columns]
    # Ensure string columns are not objects with mixed types
    for c in df.select_dtypes(include=['object']).columns:
        df[c] = df[c].astype(str)
    df.to_sql(name, conn, if_exists='replace', index=False)


def create_indexes(conn: sqlite3.Connection) -> None:
    idx_statements = [
        # games
        "CREATE INDEX IF NOT EXISTS idx_games_game_id ON games(game_id)",
        "CREATE INDEX IF NOT EXISTS idx_games_season ON games(season)",
        "CREATE INDEX IF NOT EXISTS idx_games_week ON games(week)",
        "CREATE INDEX IF NOT EXISTS idx_games_home ON games(home_team)",
        "CREATE INDEX IF NOT EXISTS idx_games_away ON games(away_team)",
        # team_games
        "CREATE INDEX IF NOT EXISTS idx_team_games_game_id ON team_games(game_id)",
        "CREATE INDEX IF NOT EXISTS idx_team_games_team ON team_games(team)",
        "CREATE INDEX IF NOT EXISTS idx_team_games_week ON team_games(week)",
        # odds
        "CREATE INDEX IF NOT EXISTS idx_odds_game_id ON odds(game_id)",
        # pfr tables
        "CREATE INDEX IF NOT EXISTS idx_pfr_team_stats_team ON pfr_team_stats(team)",
        "CREATE INDEX IF NOT EXISTS idx_pfr_team_stats_season ON pfr_team_stats(season)",
        "CREATE INDEX IF NOT EXISTS idx_pfr_team_defense_team ON pfr_team_defense(team)",
        "CREATE INDEX IF NOT EXISTS idx_pfr_team_defense_season ON pfr_team_defense(season)",
        "CREATE INDEX IF NOT EXISTS idx_pfr_games_season ON pfr_games(season)",
        "CREATE INDEX IF NOT EXISTS idx_pfr_team_gamelogs_team ON pfr_team_gamelogs(team)",
        "CREATE INDEX IF NOT EXISTS idx_pfr_team_gamelogs_season ON pfr_team_gamelogs(season)",
    ]
    for stmt in idx_statements:
        try:
            conn.execute(stmt)
        except Exception as e:
            logger.warning(f"Index create failed: {stmt} -> {e}")
    conn.commit()


def load_excel_tables() -> dict:
    tables = {}
    # Historical workbook preferred for unified games
    if WB_HIST.exists():
        xl = pd.ExcelFile(WB_HIST)
        for sheet in WB_HIST_SHEETS:
            if sheet in xl.sheet_names:
                df = pd.read_excel(WB_HIST, sheet_name=sheet)
                tables[sheet if sheet != 'games' else 'games'] = df
    else:
        logger.warning(f"Historical workbook not found: {WB_HIST}")
    
    # 2025 workbook for team_games and other tabs (skip 'games' to avoid overriding integrated games)
    if WB_2025.exists():
        xl2 = pd.ExcelFile(WB_2025)
        for sheet in WB_SHEETS_2025:
            if sheet in xl2.sheet_names and sheet != 'games':
                df = pd.read_excel(WB_2025, sheet_name=sheet)
                tables[sheet] = df
    else:
        logger.error(f"2025 workbook not found: {WB_2025}")
    return tables


def load_pfr_csvs() -> dict:
    out = {}
    if not PFR_DIR.exists():
        logger.warning(f"PFR dir not found: {PFR_DIR}")
        return out
    
    # Helper to add season from filename
    def add_season(df: pd.DataFrame, f: Path) -> pd.DataFrame:
        df = df.copy()
        year = None
        try:
            year = int(f.stem.split('_')[0])
            df['season'] = year
        except Exception:
            pass
        return df
    
    for f in PFR_DIR.glob('*_team_stats.csv'):
        out.setdefault('pfr_team_stats', []).append(add_season(pd.read_csv(f), f))
    for f in PFR_DIR.glob('*_team_defense.csv'):
        out.setdefault('pfr_team_defense', []).append(add_season(pd.read_csv(f), f))
    for f in PFR_DIR.glob('*_games.csv'):
        out.setdefault('pfr_games', []).append(add_season(pd.read_csv(f), f))
    for f in PFR_DIR.glob('*_team_gamelogs.csv'):
        out.setdefault('pfr_team_gamelogs', []).append(add_season(pd.read_csv(f), f))
    for stat in ['passing','rushing','receiving','defense']:
        for f in PFR_DIR.glob(f'*_advanced_{stat}.csv'):
            out.setdefault(f'pfr_advanced_{stat}', []).append(add_season(pd.read_csv(f), f))
    for stat in ['conversions','drives','scoring']:
        for f in PFR_DIR.glob(f'*_situational_{stat}.csv'):
            out.setdefault(f'pfr_situational_{stat}', []).append(add_season(pd.read_csv(f), f))
    # Concatenate lists
    for k, v in list(out.items()):
        out[k] = pd.concat(v, ignore_index=True) if isinstance(v, list) else v
    return out


def main():
    logger.info("Starting migration to SQLite...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    # Load tables
    wb_tables = load_excel_tables()
    pfr_tables = load_pfr_csvs()
    
    # Write core tables
    for name, df in wb_tables.items():
        write_table(conn, name, df)
    for name, df in pfr_tables.items():
        write_table(conn, name, df)
    
    # Indexes
    create_indexes(conn)
    
    # Vacuum
    try:
        conn.execute('VACUUM')
    except Exception:
        pass
    conn.close()
    logger.info(f"Migration complete: {DB_PATH}")


if __name__ == '__main__':
    main()
