"""
Pro Football Reference Data Source Indexer

Systematically explores PFR website to identify all available data sources
for historical NFL data (2020-2025).

This script catalogs:
- URL patterns for different data types
- Table IDs and structures
- Available statistics
- Historical data availability
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.pfr_scraper import PFRScraper
from bs4 import BeautifulSoup, Comment
import pandas as pd
import json
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler('outputs/pfr_data_index.log', mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class PFRDataIndexer:
    """Indexes all available data sources on Pro Football Reference"""
    
    # Comprehensive URL patterns for PFR data
    URL_PATTERNS = {
        # Season-level stats
        "season_overview": "/years/{year}/",
        "team_offense": "/years/{year}/",
        "team_defense": "/years/{year}/opp.htm",
        "standings": "/years/{year}/",
        
        # Game data
        "season_games": "/years/{year}/games.htm",
        "week_games": "/years/{year}/week_{week}.htm",
        
        # Advanced stats
        "passing_advanced": "/years/{year}/passing_advanced.htm",
        "rushing_advanced": "/years/{year}/rushing_advanced.htm",
        "receiving_advanced": "/years/{year}/receiving_advanced.htm",
        "defense_advanced": "/years/{year}/defense_advanced.htm",
        
        # Basic stats
        "passing": "/years/{year}/passing.htm",
        "rushing": "/years/{year}/rushing.htm",
        "receiving": "/years/{year}/receiving.htm",
        "defense": "/years/{year}/defense.htm",
        "kicking": "/years/{year}/kicking.htm",
        "returns": "/years/{year}/returns.htm",
        "scoring": "/years/{year}/scoring.htm",
        
        # Team-specific
        "team_gamelog": "/teams/{team}/{year}.htm",
        "team_roster": "/teams/{team}/{year}_roster.htm",
        
        # Special stats
        "fantasy": "/years/{year}/fantasy.htm",
        "drives": "/years/{year}/drives.htm",
        "conversions": "/years/{year}/conversions.htm",
        "redzone": "/years/{year}/redzone-scoring.htm",
        "penalties": "/years/{year}/penalties.htm",
        
        # Player stats
        "player_game_finder": "/play-index/pgl_finder.cgi",
        
        # Draft/roster
        "draft": "/years/{year}/draft.htm",
    }
    
    def __init__(self):
        self.scraper = PFRScraper()
        self.index = {
            "indexed_at": datetime.now().isoformat(),
            "url_patterns": self.URL_PATTERNS,
            "discovered_tables": {},
            "data_sources": [],
            "years_available": [],
            "teams": list(self.scraper.PFR_TO_WORKBOOK.values())
        }
    
    def explore_season_page(self, year: int):
        """Explore a season overview page to find all tables"""
        logger.info(f"\n{'='*80}")
        logger.info(f"EXPLORING {year} SEASON")
        logger.info(f"{'='*80}")
        
        url = f"{self.scraper.BASE_URL}/years/{year}/"
        soup = self.scraper._get_page(url)
        
        if not soup:
            logger.error(f"Failed to fetch {year} season page")
            return {}
        
        # Find all tables
        direct_tables = soup.find_all('table')
        comment_tables = self.scraper._extract_tables_from_comments(soup)
        
        tables_found = {}
        
        # Catalog direct tables
        logger.info(f"\nDirect Tables: {len(direct_tables)}")
        for table in direct_tables:
            table_id = table.get('id', 'NO_ID')
            if table_id and table_id != 'NO_ID':
                tables_found[table_id] = {
                    'location': 'direct',
                    'columns': self._get_table_columns(table)
                }
                logger.info(f"  - {table_id} ({len(tables_found[table_id]['columns'])} columns)")
        
        # Catalog tables in comments
        logger.info(f"\nTables in Comments: {len(comment_tables)}")
        for table_id, table in comment_tables.items():
            if table_id not in tables_found:
                tables_found[table_id] = {
                    'location': 'comment',
                    'columns': self._get_table_columns(table)
                }
                logger.info(f"  - {table_id} ({len(tables_found[table_id]['columns'])} columns)")
        
        return tables_found
    
    def explore_advanced_stats_page(self, year: int, stat_type: str):
        """Explore advanced stats pages"""
        url_map = {
            'passing': f"/years/{year}/passing_advanced.htm",
            'rushing': f"/years/{year}/rushing_advanced.htm",
            'receiving': f"/years/{year}/receiving_advanced.htm",
            'defense': f"/years/{year}/defense_advanced.htm"
        }
        
        if stat_type not in url_map:
            return {}
        
        url = self.scraper.BASE_URL + url_map[stat_type]
        logger.info(f"\nExploring {stat_type} advanced stats...")
        
        soup = self.scraper._get_page(url)
        if not soup:
            logger.warning(f"  Failed to fetch {stat_type} advanced stats")
            return {}
        
        tables = soup.find_all('table')
        comment_tables = self.scraper._extract_tables_from_comments(soup)
        
        tables_found = {}
        for table in tables:
            table_id = table.get('id', 'NO_ID')
            if table_id and table_id != 'NO_ID':
                tables_found[table_id] = {
                    'location': 'direct',
                    'stat_type': stat_type,
                    'columns': self._get_table_columns(table)
                }
                logger.info(f"  Found: {table_id} ({len(tables_found[table_id]['columns'])} columns)")
        
        for table_id, table in comment_tables.items():
            if table_id not in tables_found:
                tables_found[table_id] = {
                    'location': 'comment',
                    'stat_type': stat_type,
                    'columns': self._get_table_columns(table)
                }
                logger.info(f"  Found: {table_id} ({len(tables_found[table_id]['columns'])} columns)")
        
        return tables_found
    
    def explore_team_page(self, team: str, year: int):
        """Explore individual team page"""
        pfr_code = {v: k for k, v in self.scraper.PFR_TO_WORKBOOK.items()}.get(team, team.lower())
        url = f"{self.scraper.BASE_URL}/teams/{pfr_code}/{year}.htm"
        
        soup = self.scraper._get_page(url)
        if not soup:
            return {}
        
        tables = soup.find_all('table')
        comment_tables = self.scraper._extract_tables_from_comments(soup)
        
        tables_found = {}
        for table in tables:
            table_id = table.get('id', 'NO_ID')
            if table_id and table_id != 'NO_ID':
                tables_found[table_id] = {
                    'location': 'direct',
                    'team': team,
                    'columns': self._get_table_columns(table)
                }
        
        for table_id, table in comment_tables.items():
            if table_id not in tables_found:
                tables_found[table_id] = {
                    'location': 'comment',
                    'team': team,
                    'columns': self._get_table_columns(table)
                }
        
        return tables_found
    
    def _get_table_columns(self, table):
        """Extract column names from table"""
        columns = []
        thead = table.find('thead')
        if thead:
            header_row = thead.find_all('tr')[-1] if thead.find_all('tr') else None
            if header_row:
                for th in header_row.find_all('th'):
                    col = th.get('data-stat', th.text.strip())
                    if col:
                        columns.append(col)
        return columns
    
    def create_comprehensive_index(self, years=None, sample_team=True):
        """Create comprehensive index of all PFR data sources"""
        if years is None:
            years = [2024, 2023, 2022, 2021, 2020]
        
        logger.info("="*80)
        logger.info("PRO FOOTBALL REFERENCE - COMPREHENSIVE DATA INDEX")
        logger.info("="*80)
        logger.info(f"\nIndexing years: {years}")
        
        all_tables = {}
        
        # 1. Explore season overview pages
        logger.info("\n" + "="*80)
        logger.info("PHASE 1: Season Overview Pages")
        logger.info("="*80)
        
        for year in years:
            tables = self.explore_season_page(year)
            for table_id, info in tables.items():
                if table_id not in all_tables:
                    all_tables[table_id] = info.copy()
                    all_tables[table_id]['first_seen'] = year
                    all_tables[table_id]['years'] = [year]
                else:
                    all_tables[table_id]['years'].append(year)
        
        # 2. Explore advanced stats pages
        logger.info("\n" + "="*80)
        logger.info("PHASE 2: Advanced Statistics Pages")
        logger.info("="*80)
        
        advanced_types = ['passing', 'rushing', 'receiving', 'defense']
        for stat_type in advanced_types:
            for year in years[:2]:  # Sample first 2 years
                tables = self.explore_advanced_stats_page(year, stat_type)
                for table_id, info in tables.items():
                    if table_id not in all_tables:
                        all_tables[table_id] = info.copy()
                        all_tables[table_id]['first_seen'] = year
                        all_tables[table_id]['years'] = [year]
        
        # 3. Sample team page
        if sample_team:
            logger.info("\n" + "="*80)
            logger.info("PHASE 3: Team Game Log Page (Sample: NWE)")
            logger.info("="*80)
            
            tables = self.explore_team_page('NWE', years[0])
            logger.info(f"\nFound {len(tables)} tables on team page:")
            for table_id, info in tables.items():
                logger.info(f"  - {table_id} ({len(info['columns'])} columns)")
                if table_id not in all_tables:
                    all_tables[table_id] = info.copy()
                    all_tables[table_id]['first_seen'] = years[0]
        
        self.index['discovered_tables'] = all_tables
        self.index['years_available'] = years
        
        return all_tables
    
    def categorize_data_sources(self):
        """Categorize discovered tables by data type"""
        categories = {
            "Team Season Stats": [],
            "Team Game Logs": [],
            "Player Stats": [],
            "Advanced Analytics": [],
            "Game Results": [],
            "Special Teams": [],
            "Situational": [],
            "Other": []
        }
        
        for table_id, info in self.index['discovered_tables'].items():
            # Categorize based on table ID patterns
            if 'team_stats' in table_id or 'AFC' in table_id or 'NFC' in table_id:
                categories["Team Season Stats"].append(table_id)
            elif 'games' in table_id or 'schedule' in table_id:
                categories["Game Results"].append(table_id)
            elif 'passing' in table_id or 'rushing' in table_id or 'receiving' in table_id:
                if 'advanced' in info.get('stat_type', ''):
                    categories["Advanced Analytics"].append(table_id)
                else:
                    categories["Player Stats"].append(table_id)
            elif 'defense' in table_id:
                if 'advanced' in info.get('stat_type', ''):
                    categories["Advanced Analytics"].append(table_id)
                else:
                    categories["Player Stats"].append(table_id)
            elif 'kicking' in table_id or 'returns' in table_id or 'scoring' in table_id:
                categories["Special Teams"].append(table_id)
            elif 'drives' in table_id or 'redzone' in table_id or 'conversions' in table_id:
                categories["Situational"].append(table_id)
            else:
                categories["Other"].append(table_id)
        
        return categories
    
    def generate_report(self, output_file='outputs/pfr_data_index.json'):
        """Generate comprehensive report of data sources"""
        categories = self.categorize_data_sources()
        
        self.index['categories'] = categories
        
        # Save JSON index
        output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
        
        logger.info("\n" + "="*80)
        logger.info("DATA SOURCE SUMMARY")
        logger.info("="*80)
        
        logger.info(f"\nTotal unique tables discovered: {len(self.index['discovered_tables'])}")
        logger.info(f"Years indexed: {self.index['years_available']}")
        
        logger.info("\n--- By Category ---")
        for category, tables in categories.items():
            if tables:
                logger.info(f"\n{category}: {len(tables)} tables")
                for table_id in sorted(tables):
                    info = self.index['discovered_tables'][table_id]
                    logger.info(f"  - {table_id} ({len(info.get('columns', []))} cols)")
        
        logger.info(f"\n\nFull index saved to: {output_path}")
        logger.info(f"Log file saved to: outputs/pfr_data_index.log")
        
        return self.index


def main():
    """Run comprehensive PFR data indexing"""
    indexer = PFRDataIndexer()
    
    # Index 5 years of data
    years = [2024, 2023, 2022, 2021, 2020]
    
    # Create comprehensive index
    indexer.create_comprehensive_index(years=years, sample_team=True)
    
    # Generate report
    index = indexer.generate_report()
    
    # Create markdown summary
    create_markdown_summary(index)


def create_markdown_summary(index):
    """Create human-readable markdown summary"""
    output = []
    output.append("# Pro Football Reference Data Source Index")
    output.append(f"\n**Indexed**: {index['indexed_at']}")
    output.append(f"\n**Years**: {', '.join(map(str, index['years_available']))}")
    output.append(f"\n**Total Tables**: {len(index['discovered_tables'])}")
    
    output.append("\n## Data Sources by Category\n")
    
    for category, tables in index['categories'].items():
        if tables:
            output.append(f"\n### {category} ({len(tables)} tables)\n")
            for table_id in sorted(tables):
                info = index['discovered_tables'][table_id]
                cols = len(info.get('columns', []))
                years = info.get('years', [])
                output.append(f"- **{table_id}** ({cols} columns)")
                if years:
                    output.append(f"  - Years: {min(years)}-{max(years)}")
                if 'stat_type' in info:
                    output.append(f"  - Type: {info['stat_type']}")
                output.append("")
    
    output.append("\n## URL Patterns\n")
    for name, pattern in index['url_patterns'].items():
        output.append(f"- **{name}**: `{pattern}`")
    
    output.append("\n## Teams Available\n")
    output.append(f"{len(index['teams'])} teams: {', '.join(index['teams'])}")
    
    output.append("\n## Next Steps\n")
    output.append("1. Review discovered tables and prioritize for extraction")
    output.append("2. Update scraper to handle all identified table types")
    output.append("3. Create backfill script for historical data (2020-2024)")
    output.append("4. Test extraction for each table type")
    output.append("5. Integrate into model workbook")
    
    md_path = Path("outputs/pfr_data_index.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    logger.info(f"\nMarkdown summary saved to: {md_path}")


if __name__ == "__main__":
    main()
