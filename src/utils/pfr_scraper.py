"""
Pro Football Reference Web Scraper
Extracts NFL team and player statistics from pro-football-reference.com

RATE LIMITING:
- Maximum 10 requests per minute per page
- Built-in delays and request throttling
- Respectful crawling with User-Agent headers
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Ensures we don't exceed 10 requests per minute"""
    
    def __init__(self, max_requests_per_minute=10):
        self.max_requests = max_requests_per_minute
        self.requests = []
        self.min_interval = 60.0 / max_requests_per_minute  # seconds between requests
    
    def wait_if_needed(self):
        """Wait if we're approaching rate limit"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        # If we've hit the limit, wait
        if len(self.requests) >= self.max_requests:
            sleep_time = 60 - (now - self.requests[0]) + 1  # Add 1 second buffer
            logger.warning(f"Rate limit approached. Sleeping for {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
            self.requests = []
        
        # Always wait minimum interval between requests
        if self.requests:
            time_since_last = now - self.requests[-1]
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
        
        self.requests.append(time.time())


class PFRScraper:
    """Scraper for Pro Football Reference statistics"""
    
    BASE_URL = "https://www.pro-football-reference.com"
    
    # Team code mappings (PFR codes to our workbook codes)
    PFR_TO_WORKBOOK = {
        'nwe': 'NWE', 'buf': 'BUF', 'mia': 'MIA', 'nyj': 'NYJ',
        'pit': 'PIT', 'rav': 'BAL', 'cin': 'CIN', 'cle': 'CLE',
        'jax': 'JAX', 'htx': 'HOU', 'clt': 'IND', 'oti': 'TEN',
        'den': 'DEN', 'sdg': 'LAC', 'kan': 'KAN', 'rai': 'LVR',
        'phi': 'PHI', 'dal': 'DAL', 'was': 'WAS', 'nyg': 'NYG',
        'chi': 'CHI', 'gnb': 'GNB', 'min': 'MIN', 'det': 'DET',
        'car': 'CAR', 'tam': 'TAM', 'atl': 'ATL', 'nor': 'NOR',
        'sea': 'SEA', 'ram': 'LAR', 'sfo': 'SFO', 'crd': 'ARI'
    }
    
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests_per_minute=10)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NFL Stats Research Bot',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def _get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page with rate limiting"""
        self.rate_limiter.wait_if_needed()
        
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _extract_tables_from_comments(self, soup: BeautifulSoup) -> Dict[str, BeautifulSoup]:
        """
        PFR hides many tables in HTML comments to prevent scraping.
        This extracts and parses those tables.
        """
        from bs4 import Comment
        
        tables = {}
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        
        for comment in comments:
            # Parse comment as HTML
            comment_soup = BeautifulSoup(comment, 'html.parser')
            
            # Find all tables in this comment
            for table in comment_soup.find_all('table'):
                table_id = table.get('id')
                if table_id:
                    tables[table_id] = table
        
        return tables
    
    def get_team_stats(self, season: int = 2025) -> pd.DataFrame:
        """
        Fetch team offensive and defensive statistics for a season
        
        Returns DataFrame with columns:
        - team: Team code
        - games: Games played
        - points_for: Points scored
        - yards_offense: Total offensive yards
        - plays_offense: Total offensive plays
        - yards_per_play: Yards per play
        - turnovers_lost: Turnovers lost
        - fumbles_lost: Fumbles lost
        - first_downs: First downs
        - pass_completions: Pass completions
        - pass_attempts: Pass attempts
        - pass_yards: Passing yards
        - pass_tds: Passing touchdowns
        - interceptions: Interceptions thrown
        - rush_attempts: Rush attempts
        - rush_yards: Rushing yards
        - rush_tds: Rushing touchdowns
        - penalties: Penalties
        - penalty_yards: Penalty yards
        - points_against: Points allowed
        - yards_defense: Total yards allowed
        - plays_defense: Defensive plays
        (and many more defensive stats)
        """
        url = f"{self.BASE_URL}/years/{season}/"
        soup = self._get_page(url)
        
        if not soup:
            return pd.DataFrame()
        
        # Extract tables from HTML comments
        comment_tables = self._extract_tables_from_comments(soup)
        
        # Find the team stats tables (they're usually in comments)
        team_stats = []
        
        # Offensive stats table
        off_table = soup.find('table', {'id': 'team_stats'})
        if not off_table and 'team_stats' in comment_tables:
            off_table = comment_tables['team_stats']
        
        if off_table:
            team_stats.append(self._parse_stats_table(off_table, 'offense'))
        
        # Defensive stats table  
        def_table = soup.find('table', {'id': 'team_stats_opp'})  
        if not def_table and 'team_stats_opp' in comment_tables:
            def_table = comment_tables['team_stats_opp']
            
        if def_table:
            defense_df = self._parse_stats_table(def_table, 'defense')
            if not team_stats:
                team_stats.append(defense_df)
            else:
                team_stats[0] = team_stats[0].merge(defense_df, on='team', how='outer')
        
        if team_stats:
            df = team_stats[0]
            df['season'] = season
            # Convert PFR codes to workbook codes
            if 'team' in df.columns:
                df['team'] = df['team'].str.lower().map(self.PFR_TO_WORKBOOK).fillna(df['team'])
            return df
        
        return pd.DataFrame()
    
    def get_team_defense_stats(self, season: int = 2025) -> pd.DataFrame:
        """
        Fetch defensive statistics (opponent stats)
        This is separate from team_stats which focuses on offense
        
        Returns DataFrame with defensive metrics
        """
        url = f"{self.BASE_URL}/years/{season}/opp.htm"
        soup = self._get_page(url)
        
        if not soup:
            return pd.DataFrame()
        
        # First try direct tables
        tables = soup.find_all('table')
        defense_dfs = []
        
        for table in tables:
            if table.get('id') in ['team_stats', 'AFC', 'NFC']:
                df = self._parse_stats_table(table, prefix='def')
                if not df.empty:
                    defense_dfs.append(df)
        
        # Also check HTML comments for hidden tables
        comment_tables = self._extract_tables_from_comments(soup)
        for table in comment_tables.values():
            table_id = table.get('id', '')
            if 'team_stats' in table_id or table_id in ['team_stats', 'AFC', 'NFC']:
                df = self._parse_stats_table(table, prefix='def')
                if not df.empty:
                    defense_dfs.append(df)
        
        if defense_dfs:
            df = defense_dfs[0]
            df['season'] = season
            # Convert PFR codes to workbook codes
            if 'team' in df.columns:
                df['team'] = df['team'].str.lower().map(self.PFR_TO_WORKBOOK).fillna(df['team'])
            return df
        
        return pd.DataFrame()
    
    def get_situational_stats(self, season: int = 2025) -> Dict[str, pd.DataFrame]:
        """
        Fetch situational statistics (red zone, conversions, drives, penalties)
        
        Returns dict with keys: 'redzone', 'conversions', 'drives', 'scoring'
        """
        stats = {}
        
        # Main season page has several situational tables
        url = f"{self.BASE_URL}/years/{season}/"
        soup = self._get_page(url)
        
        if not soup:
            return stats
        
        # Tables to extract
        target_tables = {
            'team_conversions': 'conversions',
            'drives': 'drives',
            'team_scoring': 'scoring',
        }
        
        # Extract from comments (PFR hides most tables there)
        comment_tables = self._extract_tables_from_comments(soup)

        for table in comment_tables.values():
            table_id = table.get('id', '')
            if table_id in target_tables:
                df = self._parse_stats_table(table)
                if not df.empty:
                    df['season'] = season
                    if 'team' in df.columns:
                        df['team'] = df['team'].str.lower().map(self.PFR_TO_WORKBOOK).fillna(df['team'])
                    stats[target_tables[table_id]] = df
        
        return stats
    
    def _parse_stats_table(self, table, prefix: str = '') -> pd.DataFrame:
        """Parse a stats table into DataFrame"""
        rows = []
        headers = []
        
        # Get headers
        thead = table.find('thead')
        if thead:
            header_row = thead.find_all('tr')[-1]  # Get last header row
            headers = [th.get('data-stat', th.text.strip()) for th in header_row.find_all('th')]
        
        # Get data rows
        tbody = table.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                if 'thead' in tr.get('class', []):
                    continue
                
                row_data = {}
                for td in tr.find_all(['td', 'th']):
                    stat_name = td.get('data-stat', '')
                    value = td.text.strip()
                    
                    if stat_name:
                        # Add prefix for defense/offense distinction
                        col_name = f"{prefix}_{stat_name}" if prefix and stat_name != 'team' else stat_name
                        row_data[col_name] = value
                
                if row_data:
                    rows.append(row_data)
        
        df = pd.DataFrame(rows)
        
        # Convert numeric columns (coerce non-numeric to NaN to avoid deprecation warnings)
        for col in df.columns:
            if col != 'team':
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    
    def get_game_scores(self, season: int = 2025, week: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch game scores and basic game information
        
        Returns DataFrame with:
        - week
        - date
        - time
        - away_team
        - home_team
        - away_score
        - home_score
        - boxscore_url
        """
        if week:
            url = f"{self.BASE_URL}/years/{season}/week_{week}.htm"
        else:
            url = f"{self.BASE_URL}/years/{season}/games.htm"
        
        soup = self._get_page(url)
        if not soup:
            return pd.DataFrame()
        
        table = soup.find('table', {'id': 'games'})
        if not table:
            return pd.DataFrame()
        
        games = []
        for tr in table.find('tbody').find_all('tr'):
            if 'thead' in tr.get('class', []):
                continue
            
            game = {}
            for td in tr.find_all(['td', 'th']):
                stat = td.get('data-stat', '')
                if stat:
                    game[stat] = td.text.strip()
                    
                    # Get boxscore link
                    if stat == 'boxscore_word':
                        link = td.find('a')
                        if link:
                            game['boxscore_url'] = self.BASE_URL + link.get('href', '')
            
            if game:
                games.append(game)
        
        df = pd.DataFrame(games)
        
        # Convert team codes
        if 'winner' in df.columns:
            df['winner'] = df['winner'].str.lower().map(self.PFR_TO_WORKBOOK).fillna(df['winner'])
        if 'loser' in df.columns:
            df['loser'] = df['loser'].str.lower().map(self.PFR_TO_WORKBOOK).fillna(df['loser'])
        
        # Add season column for downstream integration
        df['season'] = season
        
        return df
    
    def get_team_game_log(self, team: str, season: int = 2025) -> pd.DataFrame:
        """
        Fetch detailed game-by-game stats for a team
        
        Args:
            team: Workbook team code (e.g., 'NWE', 'BUF')
            season: NFL season year
        
        Returns DataFrame with game-by-game offensive and defensive stats
        """
        # Convert workbook code to PFR code
        pfr_code = {v: k for k, v in self.PFR_TO_WORKBOOK.items()}.get(team, team.lower())
        
        url = f"{self.BASE_URL}/teams/{pfr_code}/{season}.htm"
        soup = self._get_page(url)
        
        if not soup:
            return pd.DataFrame()
        
        # Find game log table
        table = soup.find('table', {'id': 'games'})
        if not table:
            return pd.DataFrame()
        
        return self._parse_stats_table(table)
    
    def get_advanced_stats(self, season: int = 2025) -> Dict[str, pd.DataFrame]:
        """
        Fetch advanced statistics (passing, rushing, receiving, defense)
        
        Returns dict with keys: 'passing', 'rushing', 'receiving', 'defense'
        Each contains aggregated team statistics
        """
        stats = {}
        
        endpoints = {
            'passing': f'/years/{season}/passing_advanced.htm',
            'rushing': f'/years/{season}/rushing_advanced.htm',
            'receiving': f'/years/{season}/receiving_advanced.htm',
            'defense': f'/years/{season}/defense_advanced.htm'
        }
        
        for stat_type, endpoint in endpoints.items():
            url = self.BASE_URL + endpoint
            soup = self._get_page(url)
            
            if soup:
                table = soup.find('table')
                if table:
                    df = self._parse_stats_table(table, stat_type)
                    # Aggregate by team if player-level data
                    if 'team' in df.columns:
                        # This is player data, need to aggregate
                        numeric_cols = df.select_dtypes(include=['number']).columns
                        stats[stat_type] = df.groupby('team')[numeric_cols].sum().reset_index()
                    else:
                        stats[stat_type] = df
        
        return stats
    
    def get_injury_report(self, season: int = 2025, week: int = 1) -> pd.DataFrame:
        """
        Attempt to fetch injury report data (may require subscription)
        
        Returns DataFrame with injury information if available
        """
        url = f"{self.BASE_URL}/years/{season}/injuries.htm"
        soup = self._get_page(url)
        
        if not soup:
            logger.warning("Injury report not accessible (may require subscription)")
            return pd.DataFrame()
        
        table = soup.find('table')
        if table:
            return self._parse_stats_table(table)
        
        return pd.DataFrame()
    
    def scrape_season_data(self, season: int = 2025, output_dir: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
        """
        Comprehensive season data scrape
        
        Fetches:
        - Team stats (offense/defense)
        - Game scores  
        - Advanced stats
        - Individual team game logs (for all 32 teams)
        
        Saves to CSV files if output_dir provided
        
        Returns dict with all dataframes
        """
        logger.info(f"Starting comprehensive scrape for {season} season...")
        
        data = {}
        
        # 1. Team stats
        logger.info("Fetching team statistics...")
        data['team_stats'] = self.get_team_stats(season)
        
        # 2. Game scores
        logger.info("Fetching game scores...")
        data['game_scores'] = self.get_game_scores(season)
        
        # 3. Advanced stats
        logger.info("Fetching advanced statistics...")
        adv_stats = self.get_advanced_stats(season)
        data.update(adv_stats)
        
        # 4. Team game logs (this will take time due to rate limiting)
        logger.info("Fetching team game logs (this may take several minutes)...")
        all_game_logs = []
        
        for team_code in self.PFR_TO_WORKBOOK.values():
            logger.info(f"  Fetching game log for {team_code}...")
            game_log = self.get_team_game_log(team_code, season)
            if not game_log.empty:
                game_log['team'] = team_code
                all_game_logs.append(game_log)
        
        if all_game_logs:
            data['team_game_logs'] = pd.concat(all_game_logs, ignore_index=True)
        
        # Save to files if output directory provided
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for name, df in data.items():
                if not df.empty:
                    filename = output_dir / f"{name}_{season}_{timestamp}.csv"
                    df.to_csv(filename, index=False)
                    logger.info(f"Saved {name} to {filename}")
        
        logger.info(f"Scrape complete! Collected {len(data)} datasets.")
        return data


# Example usage functions
def scrape_current_season(output_dir: str = "data/pfr_scraped"):
    """Scrape current season data"""
    scraper = PFRScraper()
    return scraper.scrape_season_data(season=2025, output_dir=Path(output_dir))


def quick_team_stats(season: int = 2025) -> pd.DataFrame:
    """Quick fetch of team statistics"""
    scraper = PFRScraper()
    return scraper.get_team_stats(season)


def get_weekly_scores(season: int = 2025, week: int = 1) -> pd.DataFrame:
    """Get scores for a specific week"""
    scraper = PFRScraper()
    return scraper.get_game_scores(season, week)


if __name__ == "__main__":
    # Test the scraper
    print("Testing PFR Scraper...")
    print("\nFetching team stats for 2025...")
    
    scraper = PFRScraper()
    team_stats = scraper.get_team_stats(2025)
    
    if not team_stats.empty:
        print(f"\nFound stats for {len(team_stats)} teams")
        print("\nSample data:")
        print(team_stats.head())
        print("\nColumns available:")
        print(team_stats.columns.tolist())
    else:
        print("No data retrieved")
