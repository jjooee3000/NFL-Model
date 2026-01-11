#!/usr/bin/env python3
"""
Fetch game scores from ESPN for postgame evaluation
"""
import requests
import re
import json
from pathlib import Path

def fetch_espn_scores(date='2026-01-10'):
    """Fetch NFL scores from ESPN for a given date"""
    date_fmt = date.replace('-', '')
    url = f'https://www.espn.com/nfl/scoreboard/?date={date_fmt}'
    
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        text = resp.text
        
        # Look for team patterns and final scores
        # ESPN pages typically contain game data in HTML or embedded JSON
        
        # Try to find "Final" game blocks with scores
        print(f"Fetching from {url}")
        print(f"Response length: {len(text)} chars")
        
        # Look for specific team names and associated scores
        games = {}
        
        # Pattern: Look for team name followed by score in close proximity
        # Example: "Los Angeles Rams" followed by a number like "27"
        
        team_pairs = [
            ('Los Angeles Rams', 'Carolina Panthers', 'LAR', 'CAR'),
            ('Chicago Bears', 'Green Bay Packers', 'CHI', 'GNB'),
        ]
        
        for away_name, home_name, away_code, home_code in team_pairs:
            # Look for both team names in proximity with scores
            # Pattern: Team1 ... digit(s) ... Team2 ... digit(s)
            pattern = f'({away_name}|{home_name}).*?(\\d{{1,2}}).*?({home_name}|{away_name}).*?(\\d{{1,2}})'
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                groups = match.groups()
                # Check if this looks like a valid score block
                team1, score1, team2, score2 = groups
                
                # Filter for valid NFL scores (0-63)
                try:
                    s1, s2 = int(score1), int(score2)
                    if 0 <= s1 <= 63 and 0 <= s2 <= 63:
                        key = f"{away_code}_{home_code}"
                        if key not in games:
                            games[key] = {'away': away_name, 'home': home_name, 'away_score': s1, 'home_score': s2}
                            print(f"Found: {away_name} {s1}, {home_name} {s2}")
                except:
                    pass
        
        if games:
            return games
        
        # Alternative: Look for JSON data embedded in <script> tags
        print("\nLooking for embedded JSON data...")
        json_patterns = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.DOTALL)
        
        for json_str in json_patterns:
            try:
                data = json.loads(json_str)
                if 'description' in data and 'score' in str(data):
                    print(f"Found JSON: {data}")
            except:
                pass
        
        # If still no results, return sample output from direct inspection
        print("\nNote: ESPN page successfully fetched but score extraction needs manual inspection")
        print("This is likely because the page uses JavaScript rendering or embedded JSON")
        return {}
        
    except Exception as e:
        print(f"Error fetching ESPN: {e}")
        return {}

if __name__ == '__main__':
    scores = fetch_espn_scores('2026-01-10')
    print(f"\nFinal results: {scores}")
