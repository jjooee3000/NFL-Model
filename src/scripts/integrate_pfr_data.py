"""
Integrate Pro Football Reference scraped data into the NFL model workbook

This script:
1. Scrapes team/player stats from PFR
2. Maps to existing games in workbook
3. Adds new features to enhance model predictions
4. Handles rate limiting (max 10 requests/minute)
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import argparse

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.pfr_scraper import PFRScraper
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PFRIntegrator:
    """Integrates PFR data into model workbook"""
    
    def __init__(self, workbook_path: str):
        self.workbook_path = Path(workbook_path)
        self.scraper = PFRScraper()
        self.games_df = None
        self.teams_df = None
        
    def load_workbook(self):
        """Load existing workbook data"""
        logger.info(f"Loading workbook: {self.workbook_path}")
        
        try:
            self.games_df = pd.read_excel(self.workbook_path, sheet_name="games")
            logger.info(f"Loaded {len(self.games_df)} games")
            
            try:
                self.teams_df = pd.read_excel(self.workbook_path, sheet_name="teams")
                logger.info(f"Loaded {len(self.teams_df)} teams")
            except:
                logger.warning("No teams sheet found")
                self.teams_df = None
                
        except Exception as e:
            logger.error(f"Error loading workbook: {e}")
            raise
    
    def scrape_team_stats(self, season: int = 2025) -> pd.DataFrame:
        """Scrape comprehensive team statistics"""
        logger.info(f"\nScraping team stats for {season} season...")
        team_stats = self.scraper.get_team_stats(season)
        
        if team_stats.empty:
            logger.error("Failed to retrieve team stats")
            return pd.DataFrame()
        
        logger.info(f"Retrieved stats for {len(team_stats)} teams")
        logger.info(f"Available columns: {team_stats.columns.tolist()}")
        
        return team_stats
    
    def scrape_game_scores(self, season: int = 2025) -> pd.DataFrame:
        """Scrape game scores and box score links"""
        logger.info(f"\nScraping game scores for {season} season...")
        games = self.scraper.get_game_scores(season)
        
        if games.empty:
            logger.error("Failed to retrieve game scores")
            return pd.DataFrame()
        
        logger.info(f"Retrieved {len(games)} games")
        return games
    
    def scrape_team_game_logs(self, season: int = 2025, teams: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Scrape game-by-game logs for teams
        
        Args:
            season: NFL season
            teams: List of team codes (if None, scrapes all 32 teams)
        """
        if teams is None:
            teams = list(self.scraper.PFR_TO_WORKBOOK.values())
        
        logger.info(f"\nScraping game logs for {len(teams)} teams...")
        logger.info(f"This will make {len(teams)} requests with rate limiting...")
        logger.info(f"Estimated time: {len(teams) * 6 / 60:.1f} minutes")
        
        game_logs = {}
        
        for i, team in enumerate(teams, 1):
            logger.info(f"[{i}/{len(teams)}] Fetching {team} game log...")
            
            try:
                log = self.scraper.get_team_game_log(team, season)
                if not log.empty:
                    game_logs[team] = log
                    logger.info(f"  ✓ Retrieved {len(log)} games for {team}")
                else:
                    logger.warning(f"  ✗ No data for {team}")
            except Exception as e:
                logger.error(f"  ✗ Error fetching {team}: {e}")
        
        return game_logs
    
    def enrich_workbook_with_pfr_stats(
        self,
        season: int = 2025,
        scrape_game_logs: bool = False,
        output_path: str = None
    ):
        """
        Main integration function - enriches workbook with PFR data
        
        Args:
            season: NFL season year
            scrape_game_logs: If True, scrapes detailed game-by-game logs (slow)
            output_path: Where to save enriched workbook (if None, uses original path with _pfr suffix)
        """
        logger.info("=" * 70)
        logger.info("PFR DATA INTEGRATION STARTING")
        logger.info("=" * 70)
        
        # Load existing data
        self.load_workbook()
        
        # 1. Scrape team stats
        team_stats = self.scrape_team_stats(season)
        
        if team_stats.empty:
            logger.error("Cannot proceed without team stats")
            return
        
        # 2. Scrape game scores
        pfr_games = self.scrape_game_scores(season)
        
        # 3. Optionally scrape detailed game logs
        game_logs = None
        if scrape_game_logs:
            game_logs = self.scrape_team_game_logs(season)
        
        # 4. Merge data into workbook
        logger.info("\n" + "=" * 70)
        logger.info("MERGING DATA INTO WORKBOOK")
        logger.info("=" * 70)
        
        enriched_games = self._merge_team_stats(self.games_df, team_stats)
        
        # 5. Save enriched workbook
        if output_path is None:
            # Create new filename with _pfr suffix
            base = self.workbook_path.stem
            output_path = self.workbook_path.parent / f"{base}_pfr.xlsx"
        else:
            output_path = Path(output_path)
        
        logger.info(f"\nSaving enriched workbook to: {output_path}")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            enriched_games.to_excel(writer, sheet_name='games', index=False)
            team_stats.to_excel(writer, sheet_name='pfr_team_stats', index=False)
            
            if not pfr_games.empty:
                pfr_games.to_excel(writer, sheet_name='pfr_game_scores', index=False)
            
            if game_logs:
                # Combine all game logs into one sheet
                all_logs = pd.concat(
                    [log.assign(team=team) for team, log in game_logs.items()],
                    ignore_index=True
                )
                all_logs.to_excel(writer, sheet_name='pfr_game_logs', index=False)
            
            # Copy other sheets if they exist
            if self.teams_df is not None:
                self.teams_df.to_excel(writer, sheet_name='teams', index=False)
        
        logger.info(f"✅ Successfully saved enriched workbook!")
        logger.info(f"\nSummary:")
        logger.info(f"  - Original games: {len(self.games_df)}")
        logger.info(f"  - Enriched games: {len(enriched_games)}")
        logger.info(f"  - New columns added: {len(enriched_games.columns) - len(self.games_df.columns)}")
        logger.info(f"  - PFR team stats: {len(team_stats)} teams")
        if game_logs:
            logger.info(f"  - Game logs scraped: {len(game_logs)} teams")
        
        return enriched_games
    
    def _merge_team_stats(self, games: pd.DataFrame, team_stats: pd.DataFrame) -> pd.DataFrame:
        """
        Merge team stats into games dataframe
        
        Adds rolling/seasonal team statistics to each game
        """
        logger.info("Merging team statistics into games...")
        
        # Identify numeric stat columns from team_stats (excluding identifiers)
        stat_cols = [col for col in team_stats.columns 
                    if col not in ['team', 'season'] and pd.api.types.is_numeric_dtype(team_stats[col])]
        
        logger.info(f"Merging {len(stat_cols)} stat columns")
        
        # Merge home team stats
        home_merge = games.merge(
            team_stats[['team'] + stat_cols],
            left_on='home_team',
            right_on='team',
            how='left',
            suffixes=('', '_home_pfr')
        )
        
        # Rename columns to indicate home team
        for col in stat_cols:
            if col in home_merge.columns:
                home_merge.rename(columns={col: f'pfr_home_{col}'}, inplace=True)
        
        # Drop duplicate team column
        if 'team' in home_merge.columns:
            home_merge.drop('team', axis=1, inplace=True)
        
        # Merge away team stats
        away_merge = home_merge.merge(
            team_stats[['team'] + stat_cols],
            left_on='away_team',
            right_on='team',
            how='left',
            suffixes=('', '_away_pfr')
        )
        
        # Rename columns to indicate away team
        for col in stat_cols:
            if col in away_merge.columns:
                away_merge.rename(columns={col: f'pfr_away_{col}'}, inplace=True)
        
        # Drop duplicate team column
        if 'team' in away_merge.columns:
            away_merge.drop('team', axis=1, inplace=True)
        
        # Create differential features (home - away)
        logger.info("Creating differential features...")
        
        for col in stat_cols:
            home_col = f'pfr_home_{col}'
            away_col = f'pfr_away_{col}'
            
            if home_col in away_merge.columns and away_col in away_merge.columns:
                diff_col = f'pfr_diff_{col}'
                away_merge[diff_col] = away_merge[home_col] - away_merge[away_col]
        
        new_cols = len(away_merge.columns) - len(games.columns)
        logger.info(f"✓ Added {new_cols} new PFR columns")
        
        return away_merge


def main():
    parser = argparse.ArgumentParser(description='Integrate PFR data into NFL model workbook')
    parser.add_argument('--workbook', type=str,
                       default='data/nfl_2025_model_data_with_moneylines.xlsx',
                       help='Path to workbook')
    parser.add_argument('--season', type=int, default=2025,
                       help='NFL season year')
    parser.add_argument('--output', type=str, default=None,
                       help='Output path for enriched workbook')
    parser.add_argument('--game-logs', action='store_true',
                       help='Scrape detailed game logs (SLOW - ~3-5 minutes)')
    parser.add_argument('--test', action='store_true',
                       help='Test mode - only scrape team stats')
    
    args = parser.parse_args()
    
    # Create integrator
    integrator = PFRIntegrator(args.workbook)
    
    if args.test:
        # Test mode - just scrape and display team stats
        logger.info("TEST MODE - Scraping team stats only")
        integrator.load_workbook()
        team_stats = integrator.scrape_team_stats(args.season)
        
        if not team_stats.empty:
            print("\n" + "=" * 70)
            print("TEAM STATS PREVIEW")
            print("=" * 70)
            print(f"\nShape: {team_stats.shape}")
            print(f"\nColumns: {team_stats.columns.tolist()}")
            print(f"\nSample data:")
            print(team_stats.head())
            
            # Save test output
            test_output = Path("outputs/pfr_test_team_stats.csv")
            test_output.parent.mkdir(exist_ok=True)
            team_stats.to_csv(test_output, index=False)
            logger.info(f"\nTest output saved to: {test_output}")
    else:
        # Full integration
        integrator.enrich_workbook_with_pfr_stats(
            season=args.season,
            scrape_game_logs=args.game_logs,
            output_path=args.output
        )


if __name__ == "__main__":
    main()
