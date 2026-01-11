"""
Shared team code normalization utilities.

Canonical codes favor modern 2-3 letter abbreviations (e.g., KC, GB, SF, NE, LV, LAC, JAX, TB, NO, LAR).
Legacy aliases from PFR/ESPN are normalized into the canonical set, and helpers convert to the
PFR-style codes used in historical training data.
"""
from typing import Dict, Tuple

# Canonical set and alias mapping (uppercase keys)
ALIAS_TO_CANONICAL: Dict[str, str] = {
    # Identity/common forms
    "ARI": "ARI", "ATL": "ATL", "BAL": "BAL", "BUF": "BUF", "CAR": "CAR", "CHI": "CHI",
    "CIN": "CIN", "CLE": "CLE", "DAL": "DAL", "DEN": "DEN", "DET": "DET", "HOU": "HOU",
    "IND": "IND", "JAX": "JAX", "KC": "KC", "LAC": "LAC", "LAR": "LAR", "MIA": "MIA",
    "MIN": "MIN", "NE": "NE", "NO": "NO", "NYG": "NYG", "NYJ": "NYJ", "PHI": "PHI",
    "PIT": "PIT", "SEA": "SEA", "SF": "SF", "TB": "TB", "TEN": "TEN", "WAS": "WAS",
    "LV": "LV",
    # PFR/legacy aliases -> canonical
    "SDG": "LAC", "SD": "LAC", "OTI": "TEN", "CLT": "IND", "STL": "LAR", "RAM": "LAR",
    "GNB": "GB", "KAN": "KC", "NOR": "NO", "NWE": "NE", "LVR": "LV", "OAK": "LV",
    "CRD": "ARI", "SFO": "SF", "JAC": "JAX", "TAM": "TB", "WSH": "WAS", "LA": "LAR",
}

# Mapping from canonical codes to the PFR-style codes used in training features
CANONICAL_TO_PFR: Dict[str, str] = {
    "KC": "KAN",
    "GB": "GNB",
    "NO": "NOR",
    "NE": "NWE",
    "LV": "LVR",
    "TB": "TAM",
    "LAC": "SDG",  # Historical PFR code for Chargers
    "SF": "SFO",
    # Teams that already match training codes map to themselves
    "ARI": "ARI", "ATL": "ATL", "BAL": "BAL", "BUF": "BUF", "CAR": "CAR", "CHI": "CHI",
    "CIN": "CIN", "CLE": "CLE", "DAL": "DAL", "DEN": "DEN", "DET": "DET", "HOU": "HOU",
    "IND": "IND", "JAX": "JAX", "LAR": "LAR", "MIA": "MIA", "MIN": "MIN", "NYG": "NYG",
    "NYJ": "NYJ", "PHI": "PHI", "PIT": "PIT", "SEA": "SEA", "TEN": "TEN", "WAS": "WAS",
}


def canonical_team(code: str) -> str:
    """Return the canonical team code for any known alias (case-insensitive)."""
    if code is None:
        return None
    upper = str(code).strip().upper()
    return ALIAS_TO_CANONICAL.get(upper, upper)


def canonical_pair(away: str, home: str) -> Tuple[str, str]:
    """Canonicalize away/home pair and return tuple."""
    return canonical_team(away), canonical_team(home)


def canonical_game_id(season: int, week: int, away: str, home: str) -> str:
    """Build a game_id using canonical team codes and zero-padded week."""
    away_c, home_c = canonical_pair(away, home)
    return f"{int(season)}_W{int(week):02d}_{away_c}_{home_c}"


def normalize_matchup_key(date_str, away: str, home: str) -> Tuple[str, str, str]:
    """Key for deduping matchups by date + canonical codes."""
    date_val = None
    if date_str is not None:
        try:
            date_val = str(date_str)[:10]
        except Exception:
            date_val = str(date_str)
    away_c, home_c = canonical_pair(away, home)
    return date_val, away_c, home_c


def to_pfr_team_code(team: str) -> str:
    """Convert canonical team code to the PFR-style code used in training data."""
    canon = canonical_team(team)
    return CANONICAL_TO_PFR.get(canon, canon)


def equivalent_codes(team: str) -> Tuple[str, ...]:
    """Return all codes that map to the same canonical code (including canonical itself)."""
    canon = canonical_team(team)
    aliases = [alias for alias, c in ALIAS_TO_CANONICAL.items() if c == canon]
    if canon not in aliases:
        aliases.append(canon)
    return tuple(sorted(set(aliases)))
