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

# Add src directory to path for imports
SRC_DIR = Path(__file__).resolve().parents[3]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

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
    return {"status": "ok", "db": str(DB_PATH)}


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
    
    health = {"status": "ok", "db": str(DB_PATH)}
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


@app.post("/ui/refresh-upcoming")
def ui_refresh_upcoming(request: Request):
    # Re-fetch upcoming and run predictions, then render home
    try:
        from utils.upcoming_games import fetch_upcoming_with_source
        upcoming, source = fetch_upcoming_with_source(days_ahead=7)
    except Exception:
        upcoming, source = [], None
    games = [f"{g['away']}@{g['home']}" for g in upcoming]
    preds = None
    if games:
        payload = PredictRequest(
            season=datetime.datetime.utcnow().year,
            week=None,
            playoffs=False,
            sync_postgame=True,
            games=games,
            train_windows=[18],
            variants=["default"],
        )
        try:
            preds = run_predictions(payload)
        except HTTPException as e:
            preds = {"status": "error", "count": 0, "predictions": [], "stdout": None, "stderr": getattr(e, 'detail', None), "cmd": None}
        except Exception as e:
            preds = {"status": "error", "count": 0, "predictions": [], "stdout": None, "stderr": str(e), "cmd": None}
    health = {"status": "ok", "db": str(DB_PATH)}
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
def list_games(season: int, week: Optional[int] = None, limit: int = 50):
    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        if week is None:
            rows = conn.execute(
                "SELECT game_id, season, week, away_team, home_team, away_score, home_score FROM games WHERE season = ? ORDER BY week, game_id LIMIT ?",
                (season, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT game_id, season, week, away_team, home_team, away_score, home_score FROM games WHERE season = ? AND week = ? ORDER BY game_id LIMIT ?",
                (season, week, limit),
            ).fetchall()
        return [dict(r) for r in rows]


@app.get("/ui/games")
def ui_games(request: Request, season: int, week: Optional[int] = None, limit: int = 50):
    games = list_games(season=season, week=week, limit=limit)
    return templates.TemplateResponse("games.html", {"request": request, "games": games, "season": season, "week": week, "title": "Games"})


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
