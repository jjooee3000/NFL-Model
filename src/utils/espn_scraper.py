"""
ESPN and alternative sources for NFL game data

Fetches postgame scores and stats from ESPN or fallback sources
"""
import requests
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

class ESPNScraper:
    """Fetch NFL game data from ESPN"""
    
    BASE_URL = "https://www.espn.com"
    
    # Team code to ESPN short name mapping
    ESPN_TEAMS = {
        'LAR': 'los-angeles-rams',
        'CAR': 'carolina-panthers',
        'CHI': 'chicago-bears',
        'GNB': 'green-bay-packers',
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_game_score(self, away_team: str, home_team: str, date: str = '2026-01-10') -> Optional[Dict[str, Any]]:
        """
        Fetch game score from ESPN scoreboard
        
        Args:
            away_team: Team code (e.g., 'LAR')
            home_team: Team code (e.g., 'CAR')
            date: Game date YYYY-MM-DD
        
        Returns:
            Dict with away_team, home_team, away_score, home_score, or None if not found
        """
        date_fmt = date.replace('-', '')
        url = f"{self.BASE_URL}/nfl/scoreboard/?date={date_fmt}"
        
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            text = resp.text
            
            # Search for sections containing both team codes and extract scores
            # Look in 500-char windows that contain both teams
            for i in range(0, len(text) - 500, 250):
                window = text[i:i+500]
                if away_team in window and home_team in window:
                    # Found a window with both teams, extract valid NFL scores
                    scores = re.findall(r'\b(\d{1,2})\b', window)
                    scores = [int(s) for s in scores if 0 <= int(s) <= 63]
                    if len(scores) >= 2:
                        return {
                            'away_team': away_team,
                            'home_team': home_team,
                            'away_score': scores[-2],
                            'home_score': scores[-1]
                        }
        
        except Exception as e:
            print(f"Error fetching from ESPN: {e}")
        
        return None
    
    def get_game_json(self, away_team: str, home_team: str, date: str = '2026-01-10') -> Optional[Dict[str, Any]]:
        """
        Try to extract JSON game data from ESPN scoreboard page
        """
        date_fmt = date.replace('-', '')
        url = f"{self.BASE_URL}/nfl/scoreboard/?date={date_fmt}"
        
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            # Find all JSON blobs in <script> tags
            scripts = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>({.*?})</script>', resp.text, re.DOTALL)
            for script in scripts:
                try:
                    data = json.loads(script)
                    # Look for Event objects with sports:Event type containing both teams
                    events = data.get('events', []) if isinstance(data, dict) else []
                    for event in events:
                        # Check if this event has both teams
                        if 'name' in event:
                            name = event['name'].lower()
                            away_lower = away_team.lower()
                            home_lower = home_team.lower()
                            if away_lower in name and home_lower in name:
                                # Found matching event
                                competitors = event.get('competitors', [])
                                if len(competitors) >= 2:
                                    scores = [c.get('score') for c in competitors]
                                    if all(s is not None for s in scores):
                                        return {
                                            'away_team': away_team,
                                            'home_team': home_team,
                                            'away_score': int(scores[0]),
                                            'home_score': int(scores[1])
                                        }
                except Exception:
                    pass
        
        except Exception as e:
            print(f"Error extracting JSON from ESPN: {e}")
        
        return None


class NFLDotComScraper:
    """Fetch NFL game data from NFL.com"""
    
    BASE_URL = "https://www.nfl.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_game_score(self, away_team: str, home_team: str, date: str = '2026-01-10') -> Optional[Dict[str, Any]]:
        """
        Fetch from NFL.com scores page
        """
        # NFL.com format: /scores/YYYYMM/DDMMYY_AWAY_HOME
        try:
            parts = date.split('-')
            year, month, day = parts[0], parts[1], parts[2]
            url = f"{self.BASE_URL}/scores/{year}{month}{day}"
            
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            # Look for team names and scores in the page
            # Pattern: Team Name (XX) at Team Name (XX) - Final
            pattern = f'({away_team}.*?Rams|{away_team}.*?Panthers|{away_team}.*?Bears|{away_team}.*?Packers).*?(\d+).*?({home_team}.*?).*?(\d+).*?Final'
            
            m = re.search(pattern, resp.text, re.IGNORECASE | re.DOTALL)
            if m:
                try:
                    scores = [int(x) for x in re.findall(r'(\d+)', m.group(0)) if int(x) < 100]
                    if len(scores) >= 2:
                        return {
                            'away_team': away_team,
                            'home_team': home_team,
                            'away_score': scores[0],
                            'home_score': scores[1]
                        }
                except Exception:
                    pass
        
        except Exception as e:
            print(f"Error fetching from NFL.com: {e}")
        
        return None


if __name__ == "__main__":
    # Test ESPN scraper
    espn = ESPNScraper()
    print("Testing ESPN scraper...")
    result = espn.get_game_score('LAR', 'CAR', '2026-01-10')
    print(f"LAR vs CAR: {result}")
    
    result = espn.get_game_score('CHI', 'GNB', '2026-01-10')
    print(f"CHI vs GNB: {result}")
