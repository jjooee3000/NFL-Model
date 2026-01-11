"""
ESPN Schedule API client for fetching upcoming NFL games.

Usage:
    from utils.schedule import fetch_upcoming_games
    games = fetch_upcoming_games(season=2025, week=19)
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional
import time


# Map ESPN team abbreviations to workbook team codes
ESPN_TO_WORKBOOK_TEAMS = {
    "ARI": "ARI", "ATL": "ATL", "BAL": "BAL", "BUF": "BUF",
    "CAR": "CAR", "CHI": "CHI", "CIN": "CIN", "CLE": "CLE",
    "DAL": "DAL", "DEN": "DEN", "DET": "DET", "GB": "GNB",
    "HOU": "HOU", "IND": "IND", "JAX": "JAX", "KC": "KAN",
    "LAC": "LAC", "LAR": "LAR", "LV": "LVR", "MIA": "MIA",
    "MIN": "MIN", "NE": "NWE", "NO": "NOR", "NYG": "NYG",
    "NYJ": "NYJ", "PHI": "PHI", "PIT": "PIT", "SEA": "SEA",
    "SF": "SFO", "TB": "TAM", "TEN": "TEN", "WAS": "WAS",
}


def fetch_espn_schedule(season: int = 2025, week: Optional[int] = None, 
                       seasontype: int = 2) -> List[Dict]:
    """
    Fetch NFL schedule from ESPN API.
    
    Args:
        season: NFL season year (default: 2025)
        week: Specific week to fetch (1-18 regular season). If None, fetches current/upcoming.
        seasontype: 1=preseason, 2=regular, 3=playoffs (default: 2)
    
    Returns:
        List of game dictionaries with keys:
        - espn_game_id: ESPN's unique game ID
        - season: Season year
        - week: Week number
        - game_date: Date string (YYYY-MM-DD)
        - game_time: Local kickoff time
        - home_team: Home team ESPN abbreviation
        - away_team: Away team ESPN abbreviation
        - home_team_full: Full home team name
        - away_team_full: Full away team name
        - venue: Stadium name
        - city: City
        - state: State
        - neutral_site: Boolean
        - completed: Boolean
    """
    # ESPN scoreboard API endpoint
    base_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    
    games = []
    
    # If no week specified, fetch current scoreboard
    if week is None:
        params = {"seasontype": seasontype} if seasontype else {}
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "events" in data:
                for event in data["events"]:
                    # Extract week from event if available
                    week_num = event.get("week", {}).get("number")
                    game_info = _parse_espn_game(event, season, week_num)
                    if game_info:
                        games.append(game_info)
        
        except requests.RequestException as e:
            print(f"Warning: Failed to fetch current games: {e}")
    
    else:
        # Fetch specific week
        weeks_to_fetch = [week] if isinstance(week, int) else range(1, 19)
        
        for wk in weeks_to_fetch:
            params = {
                "dates": season,
                "seasontype": seasontype,
                "week": wk
            }
            
            try:
                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if "events" not in data:
                    continue
                
                for event in data["events"]:
                    game_info = _parse_espn_game(event, season, wk)
                    if game_info:
                        games.append(game_info)
                
                # Rate limiting - be polite to ESPN
                if len(weeks_to_fetch) > 1:
                    time.sleep(0.5)
            
            except requests.RequestException as e:
                print(f"Warning: Failed to fetch week {wk}: {e}")
                continue
    
    return games


def _parse_espn_game(event: Dict, season: int, week: int) -> Optional[Dict]:
    """Parse a single ESPN game event into structured format."""
    try:
        game_id = event.get("id")
        name = event.get("name", "")
        short_name = event.get("shortName", "")
        date_str = event.get("date")  # ISO format datetime
        
        # Parse datetime
        if date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            game_date = dt.strftime("%Y-%m-%d")
            game_time = dt.strftime("%H:%M")
        else:
            game_date = None
            game_time = None
        
        # Get teams
        competitions = event.get("competitions", [])
        if not competitions:
            return None
        
        competition = competitions[0]
        competitors = competition.get("competitors", [])
        
        home_team = None
        away_team = None
        home_team_full = None
        away_team_full = None
        
        for comp in competitors:
            team = comp.get("team", {})
            abbr = team.get("abbreviation", "")
            full_name = team.get("displayName", "")
            is_home = comp.get("homeAway") == "home"
            
            if is_home:
                home_team = abbr
                home_team_full = full_name
            else:
                away_team = abbr
                away_team_full = full_name
        
        # Get venue info
        venue_info = competition.get("venue", {})
        venue = venue_info.get("fullName", "")
        city = venue_info.get("address", {}).get("city", "")
        state = venue_info.get("address", {}).get("state", "")
        
        # Neutral site flag
        neutral_site = competition.get("neutralSite", False)
        
        # Completion status
        status = event.get("status", {})
        completed = status.get("type", {}).get("completed", False)
        
        return {
            "espn_game_id": game_id,
            "season": season,
            "week": week,
            "game_date": game_date,
            "game_time": game_time,
            "home_team": home_team,
            "away_team": away_team,
            "home_team_full": home_team_full,
            "away_team_full": away_team_full,
            "venue": venue,
            "city": city,
            "state": state,
            "neutral_site": neutral_site,
            "completed": completed,
        }
    
    except Exception as e:
        print(f"Warning: Failed to parse game: {e}")
        return None


def fetch_upcoming_games(season: int = 2025, week: Optional[int] = None, 
                         include_completed: bool = False, seasontype: int = 2) -> List[Dict]:
    """
    Fetch upcoming (not yet completed) NFL games.
    
    Args:
        season: NFL season year
        week: Specific week (None = current scoreboard)
        include_completed: If True, include games that have finished
        seasontype: 1=preseason, 2=regular, 3=playoffs
    
    Returns:
        List of game dictionaries ready for workbook insertion
    """
    games = fetch_espn_schedule(season, week, seasontype)
    
    # Filter to upcoming games if requested
    if not include_completed:
        games = [g for g in games if not g["completed"]]
    
    # Convert ESPN team codes to workbook codes
    for game in games:
        game["home_team_wb"] = ESPN_TO_WORKBOOK_TEAMS.get(game["home_team"], game["home_team"])
        game["away_team_wb"] = ESPN_TO_WORKBOOK_TEAMS.get(game["away_team"], game["away_team"])
    
    return games


def get_current_week(season: int = 2025) -> int:
    """
    Determine current NFL week based on today's date.
    
    Simple heuristic: fetch all weeks and find first with upcoming games.
    """
    for week in range(1, 19):
        games = fetch_upcoming_games(season, week, include_completed=False)
        if games:
            return week
    
    # Default to week 18 if nothing found
    return 18


if __name__ == "__main__":
    # Test: fetch current upcoming games
    print("Fetching current upcoming games...")
    games = fetch_upcoming_games(season=2025, week=None)
    
    if games:
        print(f"\nFound {len(games)} game(s):\n")
        for g in games:
            status = "(completed)" if g['completed'] else "(upcoming)"
            print(f"  {g['away_team_wb']} @ {g['home_team_wb']} {status}")
            print(f"    Week {g['week']}, Date: {g['game_date']} {g['game_time']}")
            print(f"    Venue: {g['venue']}")
            print()
    else:
        print("No games found.")
