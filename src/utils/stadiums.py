"""
NFL stadium coordinates (latitude, longitude) for weather data fetching.

Coordinates are for the primary home stadium of each team as of 2024-2025 season.
"""

# Stadium coordinates: Team Code -> (latitude, longitude)
NFL_STADIUM_COORDS = {
    # AFC East
    "BUF": (42.7738, -78.7870),  # Highmark Stadium - Buffalo Bills
    "MIA": (25.9580, -80.2389),  # Hard Rock Stadium - Miami Dolphins
    "NWE": (42.0909, -71.2643),  # Gillette Stadium - New England Patriots
    "NYJ": (40.8135, -74.0745),  # MetLife Stadium - New York Jets
    
    # AFC North
    "BAL": (39.2780, -76.6227),  # M&T Bank Stadium - Baltimore Ravens
    "CIN": (39.0954, -84.5160),  # Paycor Stadium - Cincinnati Bengals
    "CLE": (41.5061, -81.6995),  # Cleveland Browns Stadium
    "PIT": (40.4468, -80.0158),  # Acrisure Stadium - Pittsburgh Steelers
    
    # AFC South
    "HOU": (29.6847, -95.4107),  # NRG Stadium - Houston Texans
    "IND": (39.7601, -86.1639),  # Lucas Oil Stadium (dome) - Indianapolis Colts
    "JAX": (30.3239, -81.6373),  # TIAA Bank Field - Jacksonville Jaguars
    "TEN": (36.1665, -86.7713),  # Nissan Stadium - Tennessee Titans
    
    # AFC West
    "DEN": (39.7439, -105.0201),  # Empower Field at Mile High - Denver Broncos
    "KAN": (39.0489, -94.4839),  # GEHA Field at Arrowhead Stadium - Kansas City Chiefs
    "LVR": (36.0909, -115.1833),  # Allegiant Stadium (dome) - Las Vegas Raiders
    "LAC": (33.9535, -118.3390),  # SoFi Stadium (dome) - Los Angeles Chargers
    
    # NFC East
    "DAL": (32.7473, -97.0945),  # AT&T Stadium (retractable) - Dallas Cowboys
    "NYG": (40.8135, -74.0745),  # MetLife Stadium - New York Giants
    "PHI": (39.9008, -75.1675),  # Lincoln Financial Field - Philadelphia Eagles
    "WAS": (38.9076, -76.8645),  # Northwest Stadium - Washington Commanders
    
    # NFC North
    "CHI": (41.8623, -87.6167),  # Soldier Field - Chicago Bears
    "DET": (42.3400, -83.0456),  # Ford Field (dome) - Detroit Lions
    "GNB": (44.5013, -88.0622),  # Lambeau Field - Green Bay Packers
    "MIN": (44.9738, -93.2575),  # U.S. Bank Stadium (dome) - Minnesota Vikings
    
    # NFC South
    "ATL": (33.7553, -84.4006),  # Mercedes-Benz Stadium (retractable) - Atlanta Falcons
    "CAR": (35.2258, -80.8530),  # Bank of America Stadium - Carolina Panthers
    "NOR": (29.9511, -90.0812),  # Caesars Superdome (dome) - New Orleans Saints
    "TAM": (27.9759, -82.5033),  # Raymond James Stadium - Tampa Bay Buccaneers
    
    # NFC West
    "ARI": (33.5276, -112.2626),  # State Farm Stadium (retractable) - Arizona Cardinals
    "LAR": (33.9535, -118.3390),  # SoFi Stadium (dome) - Los Angeles Rams
    "SFO": (37.4032, -121.9698),  # Levi's Stadium - San Francisco 49ers
    "SEA": (47.5952, -122.3316),  # Lumen Field - Seattle Seahawks
}

# Dome/retractable stadium flags (weather less impactful)
INDOOR_STADIUMS = {
    "IND",  # Indianapolis Colts
    "LVR",  # Las Vegas Raiders
    "LAC",  # Los Angeles Chargers
    "DET",  # Detroit Lions
    "MIN",  # Minnesota Vikings
    "NOR",  # New Orleans Saints
    "LAR",  # Los Angeles Rams
}

RETRACTABLE_STADIUMS = {
    "DAL",  # Dallas Cowboys
    "ATL",  # Atlanta Falcons
    "ARI",  # Arizona Cardinals
}


def get_stadium_coords(team_code: str) -> tuple:
    """Get (lat, lon) for a team's home stadium using 3-letter team code."""
    return NFL_STADIUM_COORDS.get(team_code)


def is_indoor_game(home_team_code: str) -> bool:
    """Check if game is in a dome or retractable stadium (weather less relevant)."""
    return home_team_code in INDOOR_STADIUMS or home_team_code in RETRACTABLE_STADIUMS
