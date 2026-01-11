"""
Shared test fixtures and configuration for pytest
"""
import sys
from pathlib import Path
import pytest
import sqlite3
import pandas as pd
from typing import Generator

# Add src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Database path
DB_PATH = PROJECT_ROOT / "data" / "nfl_model.db"


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return project root directory"""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def db_path() -> Path:
    """Return path to SQLite database"""
    return DB_PATH


@pytest.fixture(scope="function")
def db_connection(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """
    Provide a database connection for testing
    Uses transactions that are rolled back after each test
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.rollback()  # Rollback any changes made during test
    conn.close()


@pytest.fixture(scope="session")
def sample_games_data() -> pd.DataFrame:
    """
    Provide sample game data for testing
    """
    return pd.DataFrame({
        'game_id': ['2024_01_KC_BAL', '2024_01_SF_GB', '2024_01_BUF_MIA'],
        'season': [2024, 2024, 2024],
        'week': [1, 1, 1],
        'home_team': ['BAL', 'GB', 'MIA'],
        'away_team': ['KC', 'SF', 'BUF'],
        'home_score': [20, 24, 21],
        'away_score': [27, 23, 31],
    })


@pytest.fixture(scope="session")
def sample_team_stats() -> pd.DataFrame:
    """
    Provide sample team statistics for testing
    """
    return pd.DataFrame({
        'team': ['KC', 'BAL', 'SF', 'GB', 'BUF', 'MIA'],
        'season': [2024] * 6,
        'points_for': [450, 420, 460, 380, 470, 410],
        'points_against': [320, 340, 310, 360, 300, 350],
        'total_yards': [6200, 5800, 6400, 5600, 6500, 5900],
        'pass_yards': [4200, 3800, 4400, 3600, 4500, 3900],
        'rush_yards': [2000, 2000, 2000, 2000, 2000, 2000],
    })


@pytest.fixture
def mock_model_config() -> dict:
    """
    Provide mock configuration for model testing
    """
    return {
        'window': 8,
        'model_type': 'randomforest',
        'n_estimators': 100,
        'max_depth': 10,
        'random_state': 42
    }


@pytest.fixture(scope="function")
def temp_db(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary database for isolated testing
    """
    temp_db_path = tmp_path / "test_nfl_model.db"
    conn = sqlite3.connect(str(temp_db_path))
    
    # Create minimal schema
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            season INTEGER,
            week REAL,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_games (
            team TEXT,
            season INTEGER,
            week INTEGER,
            points_for INTEGER,
            points_against INTEGER,
            total_yards INTEGER
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield temp_db_path
    
    # Cleanup
    if temp_db_path.exists():
        temp_db_path.unlink()


@pytest.fixture
def api_client():
    """
    Provide FastAPI test client
    """
    from fastapi.testclient import TestClient
    import sys
    
    # Add src to path if not already there
    src_path = str(PROJECT_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    from nfl_model.services.api.app import app
    return TestClient(app)


# Markers for test categorization
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests that require external resources")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "api: marks API tests")
    config.addinivalue_line("markers", "model: marks model tests")
    config.addinivalue_line("markers", "database: marks database tests")
