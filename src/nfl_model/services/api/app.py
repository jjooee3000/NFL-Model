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
from utils.team_codes import canonical_team, canonical_game_id, normalize_matchup_key

# Add src directory to path for imports (ensure project imports work when launched via uvicorn)
SRC_DIR = Path(__file__).resolve().parents[4]  # .../src
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
def ui_games(request: Request, season: int, week: Optional[int] = None, limit: int = 50):
    games = list_games(season=season, week=week, limit=limit)

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

    for g in games:
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
