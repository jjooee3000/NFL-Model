import requests
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from utils.team_codes import canonical_team, normalize_matchup_key

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

API_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
NFL_SCORES_URL_TMPL = "https://www.nfl.com/scores/{YYYY}{MM}{DD}"


def _canonicalize_games(games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply canonical team codes and deduplicate by date + matchup."""
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for g in games:
        away = canonical_team(g.get("away"))
        home = canonical_team(g.get("home"))
        if not away or not home:
            continue
        date = g.get("date")
        key = normalize_matchup_key(date, away, home)
        if key in seen:
            continue
        seen.add(key)
        item = dict(g)
        item["away"] = away
        item["home"] = home
        item["name"] = f"{away} @ {home}"
        deduped.append(item)
    return deduped


def fetch_espn_upcoming(days_ahead: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch upcoming NFL games from ESPN scoreboard API for dates >= today.

    Returns a list of dicts: {
      'date': 'YYYY-MM-DD',
      'away': 'BUF',
      'home': 'MIA',
      'name': 'BUF @ MIA'
    }
    """
    out: List[Dict[str, Any]] = []
    today = datetime.utcnow().date()
    # Try both regular season (2) and playoffs (3)
    for season_type in [2, 3]:
        for i in range(days_ahead + 1):
            date = today + timedelta(days=i)
            try:
                params = {
                    "dates": date.strftime("%Y%m%d"),
                    "seasontype": str(season_type)
                }
                resp = requests.get(API_URL, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                events = data.get("events", [])
                for ev in events:
                    comps = ev.get("competitions", [])
                    if not comps:
                        continue
                    comp = comps[0]
                    status = comp.get("status", {}).get("type", {}).get("state")
                    # Only keep scheduled or pre games
                    if status not in ("pre", "scheduled"):
                        continue
                    teams = comp.get("competitors", [])
                    if len(teams) != 2:
                        continue
                    # Identify home/away
                    home_team = next((t for t in teams if t.get("homeAway") == "home"), None)
                    away_team = next((t for t in teams if t.get("homeAway") == "away"), None)
                    if not home_team or not away_team:
                        continue
                    home_abbr = (home_team.get("team", {}).get("abbreviation") or "").upper()
                    away_abbr = (away_team.get("team", {}).get("abbreviation") or "").upper()
                    if not home_abbr or not away_abbr:
                        continue

                    game_date = None
                    game_time = None
                    date_str = ev.get("date") or comp.get("date")
                    if date_str:
                        try:
                            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            local_dt = dt.astimezone()
                            game_date = local_dt.strftime("%Y-%m-%d")
                            game_time = local_dt.strftime("%H:%M")
                        except Exception:
                            game_date = date.isoformat()
                            game_time = None
                    week_num = ev.get("week", {}).get("number") or comp.get("week", {}).get("number")

                    out.append({
                        "date": game_date or date.isoformat(),
                        "time": game_time,
                        "away": away_abbr,
                        "home": home_abbr,
                        "name": f"{away_abbr} @ {home_abbr}",
                        "week": week_num,
                        "seasontype": season_type,
                    })
            except Exception:
                # Ignore fetch errors per-day to keep results flowing
                continue
    return _canonicalize_games(out)


def fetch_nflcom_upcoming(days_ahead: int = 7) -> List[Dict[str, Any]]:
    """Fetch upcoming games from NFL.com scores pages for today + N days.

    Parses embedded JSON-like content for home/away abbreviations.
    """
    out: List[Dict[str, Any]] = []
    today = datetime.utcnow().date()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    for i in range(days_ahead + 1):
        d = today + timedelta(days=i)
        url = NFL_SCORES_URL_TMPL.format(YYYY=d.strftime("%Y"), MM=d.strftime("%m"), DD=d.strftime("%d"))
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            text = resp.text
            # Look for away/home abbreviations in proximity (away then home)
            import re
            pattern = re.compile(
                r'"homeAway"\s*:\s*"away"[^}]*?"abbreviation"\s*:\s*"([A-Za-z]{2,3})"[^}]*?"homeAway"\s*:\s*"home"[^}]*?"abbreviation"\s*:\s*"([A-Za-z]{2,3})"',
                re.DOTALL,
            )
            for m in pattern.finditer(text):
                away_abbr = m.group(1).upper()
                home_abbr = m.group(2).upper()
                out.append({
                    "date": d.isoformat(),
                    "away": away_abbr,
                    "home": home_abbr,
                    "name": f"{away_abbr} @ {home_abbr}",
                })
        except Exception:
            continue
    return _canonicalize_games(out)


def fetch_db_upcoming() -> List[Dict[str, Any]]:
    """Fallback: fetch upcoming games from SQLite `games` where scores are NULL.

    Returns list of {date?, away, home, name}. Date may be missing if not in schema.
    """
    db_path = DATA_DIR / "nfl_model.db"
    if not db_path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            # Prefer a date column if present
            cols = [r[1] for r in conn.execute("PRAGMA table_info(games)").fetchall()]
            has_date = "game_date" in cols or "date" in cols
            if has_date:
                date_col = "game_date" if "game_date" in cols else "date"
                # Filter to dates today or later when date column is present
                today_str = datetime.utcnow().date().isoformat()
                rows = conn.execute(
                    f"SELECT {date_col} as d, away_team, home_team FROM games WHERE (home_score IS NULL OR away_score IS NULL) AND {date_col} >= ? ORDER BY d ASC LIMIT 100",
                    (today_str,)
                ).fetchall()
                for r in rows:
                    dval = r["d"]
                    # Normalize to YYYY-MM-DD
                    try:
                        dstr = str(dval)[:10]
                    except Exception:
                        dstr = None
                    out.append({
                        "date": dstr,
                        "away": str(r["away_team"]).upper(),
                        "home": str(r["home_team"]).upper(),
                        "name": f"{str(r['away_team']).upper()} @ {str(r['home_team']).upper()}",
                    })
            else:
                rows = conn.execute(
                    "SELECT away_team, home_team FROM games WHERE (home_score IS NULL OR away_score IS NULL) ORDER BY game_id ASC LIMIT 100"
                ).fetchall()
                for r in rows:
                    out.append({
                        "date": None,
                        "away": str(r["away_team"]).upper(),
                        "home": str(r["home_team"]).upper(),
                        "name": f"{str(r['away_team']).upper()} @ {str(r['home_team']).upper()}",
                    })
    except Exception:
        return []
    return _canonicalize_games(out)


def fetch_upcoming(days_ahead: int = 7) -> List[Dict[str, Any]]:
    """Fetch upcoming using ESPN first, then NFL.com, fallback to DB."""
    espn = fetch_espn_upcoming(days_ahead=days_ahead)
    if espn:
        return espn
    nfl = fetch_nflcom_upcoming(days_ahead=days_ahead)
    if nfl:
        return nfl
    return fetch_db_upcoming()


from typing import Tuple

def fetch_upcoming_with_source(days_ahead: int = 7) -> Tuple[List[Dict[str, Any]], str]:
    """Same as fetch_upcoming but returns (games, source)."""
    espn = fetch_espn_upcoming(days_ahead=days_ahead)
    if espn:
        return espn, "espn"
    nfl = fetch_nflcom_upcoming(days_ahead=days_ahead)
    if nfl:
        return nfl, "nfl.com"
    db = fetch_db_upcoming()
    return db, "db"
