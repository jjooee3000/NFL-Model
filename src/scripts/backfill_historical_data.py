"""
Historical NFL Data Backfill Script

Scrapes Pro-Football-Reference.com for historical NFL data (2020-2024)
and integrates with existing 2025 data for comprehensive model training.

Features:
- Scrapes 5 years of data (2020-2024)
- Respects 10 requests/minute rate limit
- Saves progress after each year
- Resume capability
- Multiple output formats (JSON, CSV, Excel)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.pfr_scraper import PFRScraper
import pandas as pd
import json
from datetime import datetime
import logging
import argparse
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistoricalDataBackfill:
    """Backfills historical NFL data from PFR"""
    
    def __init__(self, output_dir='data/pfr_historical'):
        self.scraper = PFRScraper()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.progress = self._load_progress()
    
    def _load_progress(self):
        """Load progress tracker to enable resume"""
        progress_file = self.output_dir / 'backfill_progress.json'
        if progress_file.exists():
            with open(progress_file, 'r') as f:
                return json.load(f)
        return {
            'completed_years': [],
            'last_update': None,
            'data_types_completed': {}
        }
    
    def _save_progress(self):
        """Save progress"""
        self.progress['last_update'] = datetime.now().isoformat()
        progress_file = self.output_dir / 'backfill_progress.json'
        with open(progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def backfill_year(self, year: int, data_types=None):
        """
        Backfill all data for a single year
        
        Args:
            year: NFL season year
            data_types: List of data types to scrape (None = all)
                - 'team_stats' (offense)
                - 'team_defense' (defense)
                - 'games'
                - 'team_game_logs'
                - 'advanced_stats'
                - 'situational_stats'
        """
        if data_types is None:
            data_types = ['team_stats', 'team_defense', 'games', 'team_game_logs', 
                         'advanced_stats', 'situational_stats']
        
        logger.info(f"\n{'='*80}")
        logger.info(f"BACKFILLING {year} SEASON")
        logger.info(f"{'='*80}")
        logger.info(f"Data types: {', '.join(data_types)}")
        
        year_data = {
            'year': year,
            'scraped_at': datetime.now().isoformat(),
            'data': {}
        }
        
        # 1. Team Stats
        if 'team_stats' in data_types:
            logger.info(f"\n[{year}] Scraping team statistics...")
            team_stats = self.scraper.get_team_stats(year)
            
            if not team_stats.empty:
                year_data['data']['team_stats'] = team_stats.to_dict('records')
                logger.info(f"  ✓ Retrieved {len(team_stats)} teams")
                
                # Save CSV
                csv_path = self.output_dir / f'{year}_team_stats.csv'
                team_stats.to_csv(csv_path, index=False)
                logger.info(f"  ✓ Saved to {csv_path}")
            else:
                logger.warning(f"  ✗ No team stats found for {year}")
        
        # 2. Team Defense Stats
        if 'team_defense' in data_types:
            logger.info(f"\n[{year}] Scraping defensive statistics...")
            defense_stats = self.scraper.get_team_defense_stats(year)
            
            if not defense_stats.empty:
                year_data['data']['team_defense'] = defense_stats.to_dict('records')
                logger.info(f"  ✓ Retrieved {len(defense_stats)} teams")
                
                # Save CSV
                csv_path = self.output_dir / f'{year}_team_defense.csv'
                defense_stats.to_csv(csv_path, index=False)
                logger.info(f"  ✓ Saved to {csv_path}")
            else:
                logger.warning(f"  ✗ No defensive stats found for {year}")
        
        # 3. Game Schedule
        if 'games' in data_types:
            logger.info(f"\n[{year}] Scraping game schedule...")
            games = self.scraper.get_game_scores(year)
            
            if not games.empty:
                year_data['data']['games'] = games.to_dict('records')
                logger.info(f"  ✓ Retrieved {len(games)} games")
                
                # Save CSV
                csv_path = self.output_dir / f'{year}_games.csv'
                games.to_csv(csv_path, index=False)
                logger.info(f"  ✓ Saved to {csv_path}")
            else:
                logger.warning(f"  ✗ No games found for {year}")
        
        # 4. Team Game Logs (ALL 32 teams)
        if 'team_game_logs' in data_types:
            logger.info(f"\n[{year}] Scraping team game logs (all 32 teams)...")
            all_teams = list(self.scraper.PFR_TO_WORKBOOK.values())
            
            all_logs = []
            for i, team in enumerate(all_teams, 1):
                logger.info(f"  [{i}/{len(all_teams)}] {team}...")
                log = self.scraper.get_team_game_log(team, year)
                
                if not log.empty:
                    log['team'] = team
                    log['year'] = year
                    all_logs.append(log)
            
            if all_logs:
                combined_logs = pd.concat(all_logs, ignore_index=True)
                year_data['data']['team_game_logs'] = combined_logs.to_dict('records')
                logger.info(f"  ✓ Retrieved {len(combined_logs)} total games")
                
                # Save CSV
                csv_path = self.output_dir / f'{year}_team_gamelogs.csv'
                combined_logs.to_csv(csv_path, index=False)
                logger.info(f"  ✓ Saved to {csv_path}")
        
        # 5. Advanced Stats (passing, rushing, receiving, defense)
        if 'advanced_stats' in data_types:
            logger.info(f"\n[{year}] Scraping advanced statistics...")
            try:
                advanced = self.scraper.get_advanced_stats(year)
                for stat_type, df in advanced.items():
                    if not df.empty:
                        year_data['data'][f'advanced_{stat_type}'] = df.to_dict('records')
                        logger.info(f"  ✓ {stat_type}: {len(df)} rows")
                        
                        # Save CSV
                        csv_path = self.output_dir / f'{year}_advanced_{stat_type}.csv'
                        df.to_csv(csv_path, index=False)
            except Exception as e:
                logger.warning(f"  ✗ Advanced stats error: {e}")
        
        # 6. Situational Stats (red zone, conversions, drives, scoring)
        if 'situational_stats' in data_types:
            logger.info(f"\n[{year}] Scraping situational statistics...")
            try:
                situational = self.scraper.get_situational_stats(year)
                for stat_type, df in situational.items():
                    if not df.empty:
                        year_data['data'][f'situational_{stat_type}'] = df.to_dict('records')
                        logger.info(f"  ✓ {stat_type}: {len(df)} rows")
                        
                        # Save CSV
                        csv_path = self.output_dir / f'{year}_situational_{stat_type}.csv'
                        df.to_csv(csv_path, index=False)
            except Exception as e:
                logger.warning(f"  ✗ Situational stats error: {e}")
        
        # Save year JSON
        json_path = self.output_dir / f'{year}_data.json'
        with open(json_path, 'w') as f:
            json.dump(year_data, f, indent=2)
        logger.info(f"\n✓ Year {year} complete - saved to {json_path}")
        
        # Update progress
        if year not in self.progress['completed_years']:
            self.progress['completed_years'].append(year)
            self.progress['completed_years'].sort()
        self.progress['data_types_completed'][str(year)] = data_types
        self._save_progress()
        
        return year_data
    
    def backfill_all(self, start_year=2020, end_year=2024, data_types=None):
        """Backfill all years in range"""
        years = list(range(start_year, end_year + 1))
        
        logger.info(f"\n{'='*80}")
        logger.info(f"HISTORICAL DATA BACKFILL")
        logger.info(f"{'='*80}")
        logger.info(f"Years: {start_year}-{end_year} ({len(years)} seasons)")
        logger.info(f"Output: {self.output_dir}")
        
        # Check what's already done
        remaining_years = [y for y in years if y not in self.progress['completed_years']]
        
        if remaining_years:
            logger.info(f"\nYears to scrape: {remaining_years}")
            if self.progress['completed_years']:
                logger.info(f"Already completed: {self.progress['completed_years']}")
        else:
            logger.info(f"\n✓ All years already completed!")
            return
        
        # Estimate time
        # team_stats (1) + team_defense (1) + games (1) + team_game_logs (32) + 
        # advanced_stats (4) + situational_stats (1) = 40 requests per year
        requests_per_year = 40
        total_requests = len(remaining_years) * requests_per_year
        estimated_minutes = (total_requests * 6) / 60  # 6 seconds per request
        logger.info(f"\nEstimated time: {estimated_minutes:.1f} minutes")
        logger.info(f"Requests: {total_requests} ({requests_per_year} per year)")
        
        # Backfill each year
        all_data = {}
        for year in remaining_years:
            year_data = self.backfill_year(year, data_types)
            all_data[year] = year_data
            
            logger.info(f"\n{'='*80}")
            logger.info(f"Progress: {len(self.progress['completed_years'])}/{len(years)} years complete")
            logger.info(f"{'='*80}")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"BACKFILL COMPLETE!")
        logger.info(f"{'='*80}")
        logger.info(f"✓ Scraped {len(remaining_years)} years")
        logger.info(f"✓ Total years in database: {len(self.progress['completed_years'])}")
        logger.info(f"✓ Output directory: {self.output_dir}")
        
        return all_data
    
    def create_consolidated_workbook(self, output_path='data/nfl_historical_data.xlsx'):
        """Create consolidated Excel workbook with all historical data"""
        logger.info(f"\n{'='*80}")
        logger.info(f"CREATING CONSOLIDATED WORKBOOK")
        logger.info(f"{'='*80}")
        
        # Collect all CSVs
        team_stats_files = sorted(self.output_dir.glob('*_team_stats.csv'))
        games_files = sorted(self.output_dir.glob('*_games.csv'))
        gamelog_files = sorted(self.output_dir.glob('*_team_gamelogs.csv'))
        
        logger.info(f"\nFound:")
        logger.info(f"  - {len(team_stats_files)} team stats files")
        logger.info(f"  - {len(games_files)} game files")
        logger.info(f"  - {len(gamelog_files)} game log files")
        
        # Combine all data
        all_team_stats = []
        all_games = []
        all_gamelogs = []
        
        for f in team_stats_files:
            df = pd.read_csv(f)
            all_team_stats.append(df)
        
        for f in games_files:
            df = pd.read_csv(f)
            all_games.append(df)
        
        for f in gamelog_files:
            df = pd.read_csv(f)
            all_gamelogs.append(df)
        
        # Create workbook
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            if all_team_stats:
                combined_team_stats = pd.concat(all_team_stats, ignore_index=True)
                combined_team_stats.to_excel(writer, sheet_name='team_stats', index=False)
                logger.info(f"\n✓ Team Stats: {len(combined_team_stats)} rows")
            
            if all_games:
                combined_games = pd.concat(all_games, ignore_index=True)
                combined_games.to_excel(writer, sheet_name='games', index=False)
                logger.info(f"✓ Games: {len(combined_games)} rows")
            
            if all_gamelogs:
                combined_gamelogs = pd.concat(all_gamelogs, ignore_index=True)
                combined_gamelogs.to_excel(writer, sheet_name='team_gamelogs', index=False)
                logger.info(f"✓ Game Logs: {len(combined_gamelogs)} rows")
        
        logger.info(f"\n✓ Saved consolidated workbook to: {output_path}")
        
        return output_path
    
    def integrate_into_main_workbook(self, 
                                     main_workbook_path='data/nfl_2025_model_data_with_moneylines.xlsx',
                                     output_path='data/nfl_model_data_historical_integrated.xlsx'):
        """
        Integrate historical data into the main model workbook
        Merges 2020-2024 data with existing 2025 data
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"INTEGRATING HISTORICAL DATA INTO MAIN WORKBOOK")
        logger.info(f"{'='*80}")
        
        main_workbook_path = Path(main_workbook_path)
        output_path = Path(output_path)
        
        if not main_workbook_path.exists():
            logger.error(f"Main workbook not found: {main_workbook_path}")
            return None
        
        logger.info(f"\nLoading main workbook: {main_workbook_path}")
        
        # Load existing 2025 data
        existing_games = pd.read_excel(main_workbook_path, sheet_name='games')
        logger.info(f"  ✓ Existing games: {len(existing_games)} rows (2025 season)")
        
        # Load all sheet names to preserve them
        excel_file = pd.ExcelFile(main_workbook_path)
        other_sheets = {}
        for sheet in excel_file.sheet_names:
            if sheet != 'games':
                other_sheets[sheet] = pd.read_excel(main_workbook_path, sheet_name=sheet)
                logger.info(f"  ✓ Loaded sheet: {sheet} ({len(other_sheets[sheet])} rows)")
        
        # Load historical game data
        logger.info(f"\nLoading historical data from: {self.output_dir}")
        games_files = sorted(self.output_dir.glob('*_games.csv'))
        
        if not games_files:
            logger.error(f"No historical game files found in {self.output_dir}")
            logger.info("Run backfill first: python src/scripts/backfill_historical_data.py")
            return None
        
        # Mapping from full team names to PFR codes
        TEAM_NAME_TO_PFR = {
            'Arizona Cardinals':'crd','Atlanta Falcons':'atl','Baltimore Ravens':'rav','Buffalo Bills':'buf',
            'Carolina Panthers':'car','Chicago Bears':'chi','Cincinnati Bengals':'cin','Cleveland Browns':'cle',
            'Dallas Cowboys':'dal','Denver Broncos':'den','Detroit Lions':'det','Green Bay Packers':'gnb',
            'Houston Texans':'htx','Indianapolis Colts':'clt','Jacksonville Jaguars':'jax','Kansas City Chiefs':'kan',
            'Las Vegas Raiders':'rai','Los Angeles Chargers':'sdg','Los Angeles Rams':'ram','Miami Dolphins':'mia',
            'Minnesota Vikings':'min','New England Patriots':'nwe','New Orleans Saints':'nor','New York Giants':'nyg',
            'New York Jets':'nyj','Philadelphia Eagles':'phi','Pittsburgh Steelers':'pit','San Francisco 49ers':'sfo',
            'Seattle Seahawks':'sea','Tampa Bay Buccaneers':'tam','Tennessee Titans':'oti','Washington Commanders':'was',
            'Washington Football Team':'was'
        }

        def map_name_to_workbook(name: str) -> str:
            pfr = TEAM_NAME_TO_PFR.get(name, None)
            if pfr:
                return self.scraper.PFR_TO_WORKBOOK.get(pfr, name)
            return name

        historical_std = []
        for f in games_files:
            year = f.stem.split('_')[0]
            df = pd.read_csv(f)
            # Ensure season column exists
            if 'season' not in df.columns:
                try:
                    df['season'] = int(year)
                except Exception:
                    df['season'] = year
            # Derive home/away and scores
            loc = df['game_location'].fillna('')
            winner_name = df['winner']
            loser_name = df['loser']
            # workbook codes
            winner = winner_name.apply(map_name_to_workbook)
            loser = loser_name.apply(map_name_to_workbook)
            is_at = (loc == '@')
            home_team = np.where(is_at, loser, winner)
            away_team = np.where(is_at, winner, loser)
            home_score = np.where(is_at, df['pts_lose'], df['pts_win'])
            away_score = np.where(is_at, df['pts_win'], df['pts_lose'])
            # Build standardized frame
            std = pd.DataFrame({
                'game_id': (
                    df['season'].astype(str) + '_W' + pd.to_numeric(df['week_num'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(2)
                    + '_' + away_team + '_' + home_team
                ),
                'season': df['season'],
                'week': pd.to_numeric(df['week_num'], errors='coerce').astype('Int64'),
                'game_date (YYYY-MM-DD)': df['game_date'],
                'home_team': home_team,
                'away_team': away_team,
                'home_score': home_score,
                'away_score': away_score,
            })
            logger.info(f"  ✓ {year}: {len(std)} games standardized")
            historical_std.append(std)

        combined_historical = pd.concat(historical_std, ignore_index=True)
        logger.info(f"\n✓ Total historical games: {len(combined_historical)}")
        
        # Align column names (PFR uses different naming)
        # Map PFR columns to main workbook columns
        pfr_to_main_columns = {
            'week_num': 'week',
            'game_date': 'game_date (YYYY-MM-DD)',
            'winner': 'home_team',  # Will need logic to determine home/away
            'loser': 'away_team',
            'pts_win': 'home_score',
            'pts_lose': 'away_score',
        }
        
        # Create game_id for historical games (format: YYYY_WXX_AWAY_HOME)
        if 'game_id' not in combined_historical.columns:
            logger.info("\nCreating game_id for historical games...")
            # Determine year/season column
            if 'season' in combined_historical.columns:
                year_series = combined_historical['season'].astype(str)
            elif 'year' in combined_historical.columns:
                year_series = combined_historical['year'].astype(str)
            else:
                year_series = pd.Series(['UNK'] * len(combined_historical))
            
            week_series = combined_historical[combined_historical.columns.intersection(['week_num','week'])].iloc[:,0] if combined_historical.columns.intersection(['week_num','week']).any() else pd.Series([0]*len(combined_historical))
            week_str = week_series.astype(str).str.zfill(2)
            away = combined_historical['loser'] if 'loser' in combined_historical.columns else pd.Series(['UNK']*len(combined_historical))
            home = combined_historical['winner'] if 'winner' in combined_historical.columns else pd.Series(['UNK']*len(combined_historical))
            
            combined_historical['game_id'] = year_series + '_W' + week_str + '_' + away + '_' + home
        
        # Merge historical and existing games
        logger.info(f"\nMerging datasets...")
        logger.info(f"  - Historical: {len(combined_historical)} games (2020-2024)")
        logger.info(f"  - Existing: {len(existing_games)} games (2025)")
        
        # Union of columns; fill missing with NaN
        all_columns = sorted(set(existing_games.columns) | set(combined_historical.columns))
        merged_hist = combined_historical.reindex(columns=all_columns)
        merged_exist = existing_games.reindex(columns=all_columns)
        merged_games = pd.concat([merged_hist, merged_exist], ignore_index=True)
        
        # Sort by date
        if 'game_date (YYYY-MM-DD)' in merged_games.columns:
            # Normalize date types to string for consistent sorting
            gd = merged_games['game_date (YYYY-MM-DD)']
            merged_games['game_date (YYYY-MM-DD)'] = pd.to_datetime(gd, errors='coerce').dt.strftime('%Y-%m-%d')
            merged_games = merged_games.sort_values('game_date (YYYY-MM-DD)')
        elif 'game_date' in merged_games.columns:
            merged_games = merged_games.sort_values('game_date')
        
        logger.info(f"\n✓ Merged games: {len(merged_games)} rows")
        years_info = 'unknown'
        if 'season' in merged_games.columns:
            years_info = sorted(merged_games['season'].unique())
        elif 'year' in merged_games.columns:
            years_info = sorted(merged_games['year'].unique())
        logger.info(f"  - Years: {years_info}")
        
        # Save integrated workbook
        logger.info(f"\nSaving integrated workbook to: {output_path}")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            merged_games.to_excel(writer, sheet_name='games', index=False)
            
            # Add all other sheets from original workbook
            for sheet_name, df in other_sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Add historical team stats as separate sheet
            team_stats_files = sorted(self.output_dir.glob('*_team_stats.csv'))
            if team_stats_files:
                all_team_stats = [pd.read_csv(f) for f in team_stats_files]
                combined_team_stats = pd.concat(all_team_stats, ignore_index=True)
                combined_team_stats.to_excel(writer, sheet_name='pfr_team_stats_historical', index=False)
                logger.info(f"  ✓ Added sheet: pfr_team_stats_historical ({len(combined_team_stats)} rows)")
            
            # Add advanced stats sheets
            for stat_type in ['passing', 'rushing', 'receiving', 'defense']:
                stat_files = sorted(self.output_dir.glob(f'*_advanced_{stat_type}.csv'))
                if stat_files:
                    all_stats = [pd.read_csv(f) for f in stat_files]
                    combined_stats = pd.concat(all_stats, ignore_index=True)
                    sheet_name = f'pfr_advanced_{stat_type}'
                    combined_stats.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.info(f"  ✓ Added sheet: {sheet_name} ({len(combined_stats)} rows)")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"INTEGRATION COMPLETE!")
        logger.info(f"{'='*80}")
        logger.info(f"✓ Output: {output_path}")
        logger.info(f"✓ Total games: {len(merged_games)} (2020-2025)")
        logger.info(f"✓ Ready for model training with 5+ years of data")
        
        return output_path


def main():
    parser = argparse.ArgumentParser(description='Backfill historical NFL data from PFR')
    parser.add_argument('--start-year', type=int, default=2020,
                       help='First year to scrape (default: 2020)')
    parser.add_argument('--end-year', type=int, default=2024,
                       help='Last year to scrape (default: 2024)')
    parser.add_argument('--output-dir', type=str, default='data/pfr_historical',
                       help='Output directory for scraped data')
    parser.add_argument('--consolidate', action='store_true',
                       help='Create consolidated Excel workbook after scraping')
    parser.add_argument('--consolidate-only', action='store_true',
                       help='Only create consolidated workbook (skip scraping)')
    parser.add_argument('--integrate', action='store_true',
                       help='Integrate historical data into main workbook after scraping')
    parser.add_argument('--integrate-only', action='store_true',
                       help='Only integrate into main workbook (skip scraping)')
    parser.add_argument('--main-workbook', type=str, 
                       default='data/nfl_2025_model_data_with_moneylines.xlsx',
                       help='Path to main workbook for integration')
    parser.add_argument('--data-types', nargs='+',
                       choices=['team_stats', 'team_defense', 'games', 'team_game_logs', 
                               'advanced_stats', 'situational_stats'],
                       help='Specific data types to scrape (default: all)')
    
    args = parser.parse_args()
    
    backfiller = HistoricalDataBackfill(output_dir=args.output_dir)
    
    if args.integrate_only:
        # Just integrate existing historical data into main workbook
        backfiller.integrate_into_main_workbook(
            main_workbook_path=args.main_workbook
        )
    elif args.consolidate_only:
        # Just create workbook from existing CSVs
        backfiller.create_consolidated_workbook()
    else:
        # Run backfill
        data_types = args.data_types if args.data_types else [
            'team_stats', 'team_defense', 'games', 'team_game_logs', 
            'advanced_stats', 'situational_stats'
        ]
        
        backfiller.backfill_all(
            start_year=args.start_year,
            end_year=args.end_year,
            data_types=data_types
        )
        
        # Consolidate if requested
        if args.consolidate:
            backfiller.create_consolidated_workbook()
        
        # Integrate into main workbook if requested
        if args.integrate:
            backfiller.integrate_into_main_workbook(
                main_workbook_path=args.main_workbook
            )


if __name__ == "__main__":
    main()
