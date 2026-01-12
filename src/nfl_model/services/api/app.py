from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import sqlite3
from pathlib import Path
import subprocess
import sys
from pydantic import BaseModel
import traceback
import datetime
import os

# Add src directory to path for imports (ensure project imports work when launched via uvicorn)
SRC_DIR = Path(__file__).resolve().parents[3]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.team_codes import canonical_team, canonical_game_id, normalize_matchup_key

app = FastAPI(title="NFL Model API", version="0.1.0")

ROOT = Path(__file__).resolve().parents[4]
DB_PATH = ROOT / "data" / "nfl_model.db"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_conn():
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail=f"DB not found: {DB_PATH}")
    return sqlite3.connect(str(DB_PATH))


def get_live_scores_from_db():
    """Fallback: Get today's games from database when ESPN API is unavailable"""
    try:
        import datetime
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        
        with get_conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT game_id, away_team, home_team, away_score, home_score, 
                       "game_date_yyyy-mm-dd", kickoff_time_local, seasontype, week
                FROM games
                WHERE "game_date_yyyy-mm-dd" BETWEEN date('now', '-1 day') AND date('now', '+1 day')
                ORDER BY "game_date_yyyy-mm-dd"
            """).fetchall()
            
            games = []
            for r in rows:
                game = {
                    'short_name': f"{r['away_team']} @ {r['home_team']}",
                    'name': f"{r['away_team']} at {r['home_team']}",
                    'away_team': r['away_team'],
                    'home_team': r['home_team'],
                    'away_score': int(r['away_score']) if r['away_score'] else 0,
                    'home_score': int(r['home_score']) if r['home_score'] else 0,
                    'date': r['game_date_yyyy-mm-dd'],
                    'state': 'post' if r['away_score'] else 'pre',
                    'status': 'Final' if r['away_score'] else 'Scheduled',
                    'status_detail': r['kickoff_time_local'] or 'TBD',
                    'is_live': False,
                    'season_type': r['seasontype'] or 2,
                    'week': r['week'] or 0
                }
                games.append(game)
            
            return {
                "status": "ok",
                "source": "database-fallback",
                "count": len(games),
                "games": games,
                "warning": "ESPN API unavailable, using database"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database fallback failed: {str(e)}",
            "games": []
        }


def ensure_error_table():
    # Create a simple error log table if it does not exist
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                path TEXT NOT NULL,
                method TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                detail TEXT,
                stack TEXT,
                user_agent TEXT
            )
            """
        )
        conn.commit()


def log_error(path: str, method: str, status_code: int, detail: Optional[str], stack: Optional[str], user_agent: Optional[str]):
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO api_error_log (ts, path, method, status_code, detail, stack, user_agent) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.datetime.utcnow().isoformat(timespec="seconds"),
                    path,
                    method,
                    status_code,
                    detail,
                    stack,
                    user_agent,
                ),
            )
            conn.commit()
    except Exception:
        # Avoid recursive failures; swallow logging issues
        pass


# Ensure table exists on startup
ensure_error_table()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    ua = request.headers.get("user-agent", "")
    log_error(
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=str(getattr(exc, "detail", exc)),
        stack=None,
        user_agent=ua,
    )
    context = {
        "request": request,
        "title": "Error",
        "status": "error",
        "status_code": exc.status_code,
        "detail": getattr(exc, "detail", None),
        "stderr": getattr(exc, "detail", None),
        "error": getattr(exc, "detail", None),
        "cmd": None,
        "count": 0,
        "predictions": [],
        "stdout": None,
    }
    if request.url.path.startswith("/ui"):
        return templates.TemplateResponse("error.html", context, status_code=exc.status_code)
    return JSONResponse({"status": "error", "error": getattr(exc, "detail", None)}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    ua = request.headers.get("user-agent", "")
    stack = traceback.format_exc()
    log_error(
        path=request.url.path,
        method=request.method,
        status_code=500,
        detail=str(exc),
        stack=stack,
        user_agent=ua,
    )
    context = {
        "request": request,
        "title": "Error",
        "status": "error",
        "status_code": 500,
        "detail": str(exc),
        "stderr": stack,
        "error": str(exc),
        "cmd": None,
        "count": 0,
        "predictions": [],
        "stdout": None,
    }
    if request.url.path.startswith("/ui"):
        return templates.TemplateResponse("error.html", context, status_code=500)
    return JSONResponse({"status": "error", "error": str(exc), "stack": stack}, status_code=500)


@app.get("/health")
def health():
    db_status = "ok" if DB_PATH.exists() else "missing"
    return {"status": "ok", "db": db_status, "db_path": str(DB_PATH)}


@app.get("/")
def index(request: Request):
    # Fetch upcoming games (fast)
    try:
        from utils.upcoming_games import fetch_upcoming_with_source
        upcoming, source = fetch_upcoming_with_source(days_ahead=7)
    except Exception:
        upcoming, source = [], None
    
    # Get cached predictions from DB instead of running them (which is slow)
    predictions = []
    if upcoming:
        with get_conn() as conn:
            conn.row_factory = sqlite3.Row
            for game in upcoming:
                away = game["away"]
                home = game["home"]
                row = conn.execute(
                    "SELECT * FROM ensemble_predictions WHERE away_team = ? AND home_team = ? ORDER BY timestamp DESC LIMIT 1",
                    (away, home),
                ).fetchone()
                if row:
                    predictions.append(dict(row))
    
    # Fetch recent predictions with actual results for performance tracking
    recent_predictions = []
    model_performance = {"mae": None, "accuracy": None, "total_predictions": 0, "correct_predictions": 0}
    
    # Get today's date to filter out ongoing games
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        # Get recent 10 COMPLETED games (not today) with most recent prediction per game
        # Use a subquery to get only the latest prediction per game_id
        recent_rows = conn.execute("""
            WITH LatestPredictions AS (
                SELECT 
                    ep.game_id, 
                    ep.away_team, 
                    ep.home_team, 
                    ep.pred_margin_home, 
                    ep.pred_total,
                    ep.timestamp,
                    ROW_NUMBER() OVER (PARTITION BY ep.game_id ORDER BY ep.timestamp DESC) as rn
                FROM ensemble_predictions ep
            )
            SELECT 
                lp.game_id, lp.away_team, lp.home_team, lp.pred_margin_home, lp.pred_total, 
                lp.timestamp, g.away_score, g.home_score, g."game_date_yyyy-mm-dd"
            FROM LatestPredictions lp
            JOIN games g ON lp.game_id = g.game_id
            WHERE lp.rn = 1
                AND g.away_score IS NOT NULL 
                AND g.home_score IS NOT NULL
                AND g."game_date_yyyy-mm-dd" < ?
            ORDER BY g."game_date_yyyy-mm-dd" DESC
            LIMIT 10
        """, (today,)).fetchall()
        
        errors = []
        for row in recent_rows:
            r = dict(row)
            actual_margin = float(r["home_score"]) - float(r["away_score"])
            pred_margin = float(r["pred_margin_home"]) if r["pred_margin_home"] else 0
            error = abs(actual_margin - pred_margin)
            errors.append(error)
            
            # Check if prediction was correct (same sign = correct winner)
            correct = (actual_margin > 0 and pred_margin > 0) or (actual_margin < 0 and pred_margin < 0) or (actual_margin == 0 and abs(pred_margin) < 3)
            
            r["actual_margin"] = actual_margin
            r["error"] = error
            r["correct"] = correct
            r["actual_total"] = float(r["home_score"]) + float(r["away_score"])
            recent_predictions.append(r)
        
        if errors:
            model_performance["mae"] = sum(errors) / len(errors)
            model_performance["total_predictions"] = len(errors)
            model_performance["correct_predictions"] = sum(1 for p in recent_predictions if p["correct"])
            model_performance["accuracy"] = (model_performance["correct_predictions"] / model_performance["total_predictions"]) * 100 if model_performance["total_predictions"] > 0 else 0
    
    # Get featured prediction (latest ensemble prediction)
    featured_prediction = None
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        # Get the most recent ensemble prediction
        featured_row = conn.execute("""
            SELECT ep.*, g."game_date_yyyy-mm-dd", g.kickoff_time_local
            FROM ensemble_predictions ep
            LEFT JOIN games g ON ep.game_id = g.game_id
            WHERE g.away_score IS NULL AND g.home_score IS NULL
            ORDER BY ep.timestamp DESC
            LIMIT 1
        """).fetchone()
        if featured_row:
            featured_prediction = dict(featured_row)
    
    # Get today's games (current/happening now)
    current_games = []
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        current_rows = conn.execute("""
            SELECT game_id, away_team, home_team, away_score, home_score, "game_date_yyyy-mm-dd", kickoff_time_local
            FROM games
            WHERE "game_date_yyyy-mm-dd" = ?
            ORDER BY kickoff_time_local
        """, (today,)).fetchall()
        current_games = [dict(r) for r in current_rows]
    
    db_status = "ok" if DB_PATH.exists() else "missing"
    health = {"status": "ok", "db": db_status, "db_path": str(DB_PATH)}
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "health": health,
            "title": "Home",
            "upcoming": upcoming,
            "upcoming_source": source,
            "predictions": predictions,
            "pred_status": "ok" if predictions else "no-cache",
            "pred_count": len(predictions),
            "current_games": current_games,
            "recent_predictions": recent_predictions[:5],
            "model_performance": model_performance,
            "featured_prediction": featured_prediction,
        },
    )


@app.get("/upcoming")
def upcoming_json(days: int = 7):
    try:
        from utils.upcoming_games import fetch_upcoming_with_source
        games, source = fetch_upcoming_with_source(days_ahead=days)
        return {"status": "ok", "source": source, "count": len(games), "games": games}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upcoming fetch failed: {e}")


@app.get("/api/live-scores")
def live_scores():
    """
    Fetch live scores from ESPN scoreboard API for all NFL games.
    Returns games with their current status (pre/in/post), scores, and game details.
    Falls back to database if ESPN API is unavailable.
    """
    try:
        import requests
        
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            # Fallback to database
            return get_live_scores_from_db()
        
        data = response.json()
        events = data.get('events', [])
        
        games = []
        for event in events:
            try:
                status_info = event['status']['type']
                state = status_info['state']  # pre, in, post
                status_name = status_info['name']
                status_detail = status_info['detail']
                
                comps = event['competitions'][0]['competitors']
                away = next(c for c in comps if c['homeAway'] == 'away')
                home = next(c for c in comps if c['homeAway'] == 'home')
                
                away_abbr = away['team']['abbreviation']
                home_abbr = home['team']['abbreviation']
                
                # Apply canonical team code mapping
                away_team = canonical_team(away_abbr)
                home_team = canonical_team(home_abbr)
                
                game = {
                    'name': event.get('name', ''),
                    'short_name': event.get('shortName', ''),
                    'date': event.get('date', ''),
                    'state': state,
                    'status': status_name,
                    'status_detail': status_detail,
                    'away_team': away_team,
                    'home_team': home_team,
                    'away_score': int(away.get('score', 0)),
                    'home_score': int(home.get('score', 0)),
                }
                
                # Extract quarter and clock info for live games
                if state == 'in':
                    game['is_live'] = True
                    game['clock'] = status_detail  # e.g., "4:33 - 3rd Quarter"
                else:
                    game['is_live'] = False
                
                # Add season info
                season_info = event.get('season', {})
                week_info = event.get('week', {})
                game['season_year'] = season_info.get('year', 0)
                game['season_type'] = season_info.get('type', 0)  # 1=pre, 2=reg, 3=post
                game['week'] = week_info.get('number', 0)
                
                games.append(game)
            except Exception as e:
                # Skip games that fail to parse
                continue
        
        return {
            "status": "ok",
            "source": "espn-live",
            "count": len(games),
            "games": games
        }
        
    except Exception as e:
        # Fallback to database on any error
        return get_live_scores_from_db()


@app.post("/ui/refresh-upcoming")
def ui_refresh_upcoming(request: Request):
    # Re-fetch upcoming and trigger predictions without blocking the request
    try:
        from utils.upcoming_games import fetch_upcoming_with_source
        upcoming, source = fetch_upcoming_with_source(days_ahead=7)
    except Exception:
        upcoming, source = [], None

    games = [f"{g['away']}@{g['home']}" for g in upcoming]
    preds = None
    playoffs = any(g.get("seasontype") == 2 for g in upcoming)
    target_week = max([g.get("week") for g in upcoming if g.get("week") is not None] or [None])
    week_for_model: Optional[int] = None
    if target_week is not None:
        week_for_model = 18 + int(target_week) if playoffs else int(target_week)

    # Derive season from DB (latest) as default to avoid mis-keying postseason
    season_from_db: Optional[int] = None
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(season) FROM games").fetchone()
        if row and row[0] is not None:
            season_from_db = int(row[0])

    target_season = season_from_db or datetime.datetime.utcnow().year

    if games and week_for_model is not None:
        python_exe = ROOT / ".venv" / "Scripts" / "python.exe"
        script = ROOT / "src" / "scripts" / "predict_ensemble_multiwindow.py"
        if not python_exe.exists() or not script.exists():
            preds = {"status": "error", "count": 0, "predictions": [], "stdout": None, "stderr": "Predict script or venv python missing", "cmd": None}
        else:
            cmd: List[str] = [str(python_exe), str(script), "--season", str(target_season), "--week", str(week_for_model), "--train-windows", "18", "--games", *games]
            if playoffs:
                cmd.append("--playoffs")
            cmd.append("--sync-postgame")

            log_path = ROOT / "outputs" / "predict_upcoming.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)

            creationflags = 0
            if sys.platform.startswith("win"):
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)

            env = os.environ.copy()
            existing_pp = env.get("PYTHONPATH", "")
            extra = str(ROOT / "src")
            env["PYTHONPATH"] = f"{extra}{os.pathsep}{existing_pp}" if existing_pp else extra

            log_file = open(log_path, "a", encoding="utf-8")
            log_file.write(f"\n[{datetime.datetime.utcnow().isoformat(timespec='seconds')}] START {' '.join(cmd)}\n")
            log_file.flush()
            try:
                subprocess.Popen(
                    cmd,
                    cwd=str(ROOT),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags,
                    env=env,
                )
            except Exception as e:
                preds = {"status": "error", "count": 0, "predictions": [], "stdout": None, "stderr": str(e), "cmd": cmd}
            finally:
                try:
                    log_file.close()
                except Exception:
                    pass

            if preds is None:
                preds = {"status": "started", "count": 0, "predictions": [], "stdout": None, "stderr": None, "cmd": cmd}

    db_status = "ok" if DB_PATH.exists() else "missing"
    health = {"status": "ok", "db": db_status, "db_path": str(DB_PATH)}
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "health": health,
            "title": "Home",
            "upcoming": upcoming,
            "upcoming_source": source,
            "predictions": (preds or {"predictions": []}).get("predictions", []),
            "pred_status": (preds or {"status": "ok"}).get("status", "ok"),
            "pred_count": (preds or {"count": 0}).get("count", 0),
        },
    )


@app.get("/games")
def list_games(season: int, week: Optional[int] = None, limit: int = 300):
    def priority(row: dict):
        home_score = row.get("home_score")
        away_score = row.get("away_score")
        complete = 1 if (home_score is not None and away_score is not None) else 0
        has_date = 1 if row.get("game_date_yyyy-mm-dd") else 0
        raw_match = 1 if row.get("raw_game_id") == row.get("game_id") else 0
        return (complete, has_date, raw_match)

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        if week is None:
            rows = conn.execute(
                """
                SELECT game_id, season, week, away_team, home_team, away_score, home_score, "game_date_yyyy-mm-dd", kickoff_time_local
                FROM games
                WHERE season = ?
                ORDER BY
                  COALESCE("game_date_yyyy-mm-dd", '') DESC,
                  COALESCE(kickoff_time_local, '') DESC,
                  week DESC,
                  game_id DESC
                LIMIT ?
                """,
                (season, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT game_id, season, week, away_team, home_team, away_score, home_score, "game_date_yyyy-mm-dd", kickoff_time_local
                FROM games
                WHERE season = ? AND week = ?
                ORDER BY COALESCE("game_date_yyyy-mm-dd", ''), COALESCE(kickoff_time_local, ''), game_id
                LIMIT ?
                """,
                (season, week, limit),
            ).fetchall()

        deduped = {}
        for r in rows:
            g = dict(r)
            g["raw_game_id"] = g.get("game_id")
            g["away_team"] = canonical_team(g.get("away_team"))
            g["home_team"] = canonical_team(g.get("home_team"))
            try:
                wk_val = int(g.get("week") or 0)
            except Exception:
                wk_val = 0
            g["game_id"] = canonical_game_id(season, wk_val, g["away_team"], g["home_team"])
            key = normalize_matchup_key(g.get("game_date_yyyy-mm-dd"), g["away_team"], g["home_team"])
            current = deduped.get(key)
            if current is None or priority(g) > priority(current):
                deduped[key] = g
        return list(deduped.values())


@app.get("/ui/games")
def ui_games(request: Request, season: Optional[int] = None, week: Optional[int] = None, page: int = 1, page_size: int = 50):
    # Default to 2025 if no season specified (current season with games)
    if season is None:
        season = 2025
    
    # Calculate limit with pagination
    limit = page * page_size
    games = list_games(season=season, week=week, limit=limit)
    
    # Paginate results
    start_idx = (page - 1) * page_size
    end_idx = page * page_size
    paginated_games = games[start_idx:end_idx]
    has_next = len(games) >= limit

    # Attach latest prediction per game and compute model miss vs actual
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        pred_map = {}
        like_clause = f"{season}_W{int(week):02d}_%" if week is not None else f"{season}_%"
        pred_rows = conn.execute(
            "SELECT game_id, away_team, home_team, pred_margin_home, pred_total, timestamp FROM ensemble_predictions WHERE game_id LIKE ? ORDER BY timestamp DESC",
            (like_clause,),
        ).fetchall()
        for row in pred_rows:
            key = (canonical_team(row["away_team"]), canonical_team(row["home_team"]))
            if key not in pred_map:
                pred_map[key] = dict(row)

    for g in paginated_games:
        pred = pred_map.get((g["away_team"], g["home_team"]), {})
        g["pred_margin_home"] = pred.get("pred_margin_home")
        g["pred_total"] = pred.get("pred_total")
        g["pred_timestamp"] = pred.get("timestamp")

        home_score = g.get("home_score")
        away_score = g.get("away_score")
        if home_score is not None and away_score is not None:
            g["actual_margin_home"] = float(home_score) - float(away_score)
            g["actual_total"] = float(home_score) + float(away_score)
        else:
            g["actual_margin_home"] = None
            g["actual_total"] = None

        if g["actual_margin_home"] is not None and g["pred_margin_home"] is not None:
            g["model_miss"] = g["actual_margin_home"] - float(g["pred_margin_home"])
        else:
            g["model_miss"] = None

    return templates.TemplateResponse("games.html", {
        "request": request, 
        "games": paginated_games, 
        "season": season, 
        "week": week, 
        "title": "Games",
        "page": page,
        "page_size": page_size,
        "has_next": has_next,
        "has_prev": page > 1
    })


def get_error_logs(limit: int = 100):
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, ts, path, method, status_code, detail, user_agent FROM api_error_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/errors")
def errors(limit: int = 100):
    return {"status": "ok", "count": len(get_error_logs(limit)), "errors": get_error_logs(limit)}


@app.get("/ui/errors")
def ui_errors(request: Request, limit: int = 100):
    logs = get_error_logs(limit)
    return templates.TemplateResponse("errors.html", {"request": request, "logs": logs, "title": "Errors"})


@app.get("/predictions/{game_id}")
def get_prediction(game_id: str):
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        # Latest prediction per game
        rows = conn.execute(
            "SELECT * FROM ensemble_predictions WHERE game_id = ? ORDER BY timestamp DESC LIMIT 1",
            (game_id,),
        ).fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="Prediction not found")
        return dict(rows[0])


class PredictRequest(BaseModel):
    season: int
    week: Optional[int] = None
    playoffs: Optional[bool] = False
    sync_postgame: Optional[bool] = True
    games: Optional[List[str]] = None
    train_windows: Optional[List[int]] = None
    variants: Optional[List[str]] = None


@app.post("/predict")
def run_predictions(req: PredictRequest):
    script = ROOT / "src" / "scripts" / "predict_ensemble_multiwindow.py"
    if not script.exists():
        raise HTTPException(status_code=500, detail=f"Script not found: {script}")
    # Use venv Python, not sys.executable (which may be system Python)
    python_exe = ROOT / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        raise HTTPException(status_code=500, detail=f"Virtual environment Python not found: {python_exe}")
    cmd: List[str] = [str(python_exe), str(script)]
    if req.sync_postgame:
        cmd.append("--sync-postgame")
    if req.season:
        cmd.extend(["--season", str(req.season)])
    # Script requires a week; default to 18 if not provided
    cmd.extend(["--week", str(req.week if req.week is not None else 18)])
    if req.playoffs:
        cmd.append("--playoffs")
    if req.train_windows:
        cmd.extend(["--train-windows", *[str(w) for w in req.train_windows]])
    if req.variants:
        cmd.extend(["--variants", *[str(v) for v in req.variants]])
    if req.games:
        cmd.extend(["--games", *req.games])
    try:
        # Increased timeout to 300s (5 minutes) to handle multiple games
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction run failed: {e}")
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Prediction script error: {proc.stderr}")
    # Return latest predictions
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        predictions: List[dict] = []
        if req.games:
            for g in req.games:
                away, home = None, None
                for sep in ["@", " @ ", " vs ", "_"]:
                    if sep in g:
                        parts = g.split(sep)
                        if len(parts) == 2:
                            away = parts[0].strip().upper()
                            home = parts[1].strip().upper()
                        break
                if away and home:
                    row = conn.execute(
                        "SELECT * FROM ensemble_predictions WHERE away_team = ? AND home_team = ? ORDER BY timestamp DESC LIMIT 1",
                        (away, home),
                    ).fetchone()
                    if row:
                        predictions.append(dict(row))
        else:
            params: List[object] = [req.season]
            where = "g.season = ?"
            if req.week is not None:
                where += " AND g.week = ?"
                params.append(req.week)
            rows = conn.execute(
                f"SELECT ep.* FROM ensemble_predictions ep JOIN games g ON g.game_id = ep.game_id WHERE {where} ORDER BY ep.timestamp DESC LIMIT 20",
                params,
            ).fetchall()
            predictions = [dict(r) for r in rows]
    return {"status": "ok", "count": len(predictions), "predictions": predictions, "stdout": proc.stdout[-1000:], "stderr": proc.stderr[-1000:], "cmd": cmd}


@app.post("/ui/predict")
def ui_predict(request: Request, season: int = Form(...), week: Optional[int] = Form(None), playoffs: Optional[bool] = Form(False), sync_postgame: Optional[bool] = Form(True)):
    payload = PredictRequest(season=season, week=week, playoffs=playoffs, sync_postgame=sync_postgame)
    try:
        res = run_predictions(payload)
        context = {"request": request, **res, "title": "Predictions"}
        return templates.TemplateResponse("predict.html", context)
    except HTTPException as e:
        # Render an error page instead of returning a 500, to aid troubleshooting
        context = {
            "request": request,
            "title": "Predictions",
            "status": "error",
            "count": 0,
            "predictions": [],
            "stdout": None,
            "stderr": getattr(e, "detail", None),
            "error": getattr(e, "detail", str(e)),
            "cmd": None,
        }
        return templates.TemplateResponse("predict.html", context, status_code=e.status_code)


@app.post("/ui/sync-postgame")
def ui_sync_postgame(request: Request, season: int = Form(...), week: Optional[int] = Form(None)):
    script = ROOT / "src" / "scripts" / "update_postgame_scores.py"
    if not script.exists():
        raise HTTPException(status_code=500, detail=f"Script not found: {script}")

    python_exe = ROOT / ".venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        raise HTTPException(status_code=500, detail=f"Virtual environment Python not found: {python_exe}")

    cmd: List[str] = [str(python_exe), str(script), "--season", str(season)]
    resolved_week = week
    if resolved_week is None:
        with get_conn() as conn:
            row = conn.execute("SELECT MAX(week) FROM games WHERE season = ?", (season,)).fetchone()
            resolved_week = int(row[0]) if row and row[0] is not None else None
    if resolved_week is not None:
        cmd.extend(["--week", str(resolved_week)])

    log_path = ROOT / "outputs" / "postgame_sync.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)

    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    extra = str(ROOT / "src")
    env["PYTHONPATH"] = f"{extra}{os.pathsep}{existing_pp}" if existing_pp else extra

    log_file = open(log_path, "a", encoding="utf-8")
    log_file.write(f"\n[{datetime.datetime.utcnow().isoformat(timespec='seconds')}] START {' '.join(cmd)}\n")
    log_file.flush()

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            env=env,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Postgame sync launch failed: {e}")
    finally:
        try:
            log_file.close()
        except Exception:
            pass

    return JSONResponse({"status": "started", "pid": proc.pid, "cmd": cmd, "log": str(log_path)})


@app.get("/ui/sync-status")
def ui_sync_status(request: Request):
    """Poll sync status by reading last lines of log file"""
    log_path = ROOT / "outputs" / "postgame_sync.log"
    if not log_path.exists():
        return JSONResponse({"status": "no_log", "message": "No sync log found"})
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            last_lines = lines[-10:] if len(lines) > 10 else lines
            last_text = "".join(last_lines)
            
            # Check for completion indicators
            if "Updated" in last_text and "games" in last_text:
                # Extract number if possible
                import re
                match = re.search(r"Updated (\d+) games", last_text)
                count = int(match.group(1)) if match else 0
                return JSONResponse({"status": "complete", "message": f"Synced {count} games", "count": count})
            elif "ERROR" in last_text or "Error" in last_text:
                return JSONResponse({"status": "error", "message": "Sync encountered an error"})
            else:
                return JSONResponse({"status": "running", "message": "Sync in progress..."})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})
