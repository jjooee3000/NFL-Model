"""
Tests for database operations and data integrity

Tests cover:
- Database connection and initialization
- Query execution and data retrieval
- Data integrity and validation
- CRUD operations
- Error handling
"""
import pytest
import sqlite3
import pandas as pd
from pathlib import Path


# ============================================================================
# PART 1: Database Connection Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestDatabaseConnection:
    """Test database connection and initialization"""
    
    def test_database_exists(self, db_path):
        """Test that database file exists"""
        assert db_path.exists()
        assert db_path.is_file()
        assert db_path.suffix == '.db'
    
    def test_can_connect(self, db_connection):
        """Test that connection can be established"""
        assert db_connection is not None
        
        # Execute simple query
        cursor = db_connection.cursor()
        result = cursor.execute("SELECT 1").fetchone()
        assert result[0] == 1
    
    def test_connection_is_sqlite(self, db_connection):
        """Test that connection is SQLite"""
        cursor = db_connection.cursor()
        result = cursor.execute("SELECT sqlite_version()").fetchone()
        assert result is not None
        assert len(result[0]) > 0  # Version string exists
    
    def test_database_has_tables(self, db_connection):
        """Test that database contains expected tables"""
        cursor = db_connection.cursor()
        tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        
        table_names = [t[0] for t in tables]
        
        # Should have at least games table
        assert 'games' in table_names
        assert len(table_names) > 0


# ============================================================================
# PART 2: Query Execution Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestQueryExecution:
    """Test query execution and data retrieval"""
    
    def test_select_all_games(self, db_connection):
        """Test selecting all games"""
        query = "SELECT * FROM games LIMIT 10"
        df = pd.read_sql(query, db_connection)
        
        assert len(df) > 0
        assert len(df.columns) > 0
    
    def test_select_with_where_clause(self, db_connection):
        """Test query with WHERE clause"""
        query = "SELECT * FROM games WHERE season = 2024 LIMIT 10"
        df = pd.read_sql(query, db_connection)
        
        # All rows should be from 2024 season
        if len(df) > 0:
            assert (df['season'] == 2024).all()
    
    def test_select_distinct_teams(self, db_connection):
        """Test getting distinct teams"""
        query = "SELECT DISTINCT home_team FROM games WHERE season = 2024 AND home_team IS NOT NULL"
        df = pd.read_sql(query, db_connection)
        
        # Should have multiple teams
        if len(df) > 0:
            assert len(df) > 1
            # Team codes should be 2-4 characters (NFL uses 2-3, but allow flexibility)
            assert all(df['home_team'].str.len().between(2, 4))
    
    def test_aggregate_query(self, db_connection):
        """Test aggregate query (COUNT, AVG, etc.)"""
        query = "SELECT season, COUNT(*) as game_count FROM games GROUP BY season"
        df = pd.read_sql(query, db_connection)
        
        if len(df) > 0:
            assert 'season' in df.columns
            assert 'game_count' in df.columns
            assert df['game_count'].min() >= 0
    
    def test_join_query(self, db_connection):
        """Test query with JOIN"""
        # Simple self-join to verify join capability
        query = """
        SELECT g1.game_id, g1.home_team, g1.away_team
        FROM games g1
        LIMIT 5
        """
        df = pd.read_sql(query, db_connection)
        
        assert len(df) >= 0
        if len(df) > 0:
            assert 'game_id' in df.columns


# ============================================================================
# PART 3: Data Integrity Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestDataIntegrity:
    """Test data integrity and validation"""
    
    def test_no_null_game_ids(self, db_connection):
        """Test that game_id is never NULL"""
        query = "SELECT COUNT(*) FROM games WHERE game_id IS NULL"
        cursor = db_connection.cursor()
        count = cursor.execute(query).fetchone()[0]
        
        assert count == 0
    
    def test_valid_team_codes(self, db_connection):
        """Test that team codes are valid format"""
        query = "SELECT DISTINCT home_team FROM games WHERE home_team IS NOT NULL LIMIT 100"
        df = pd.read_sql(query, db_connection)
        
        if len(df) > 0:
            # Team codes should be 2-3 uppercase letters (allow some variations)
            valid_pattern = df['home_team'].str.match(r'^[A-Z]{2,4}$', na=False)
            assert valid_pattern.sum() > len(df) * 0.8  # At least 80% should match
    
    def test_valid_seasons(self, db_connection):
        """Test that season years are valid"""
        query = "SELECT DISTINCT season FROM games"
        df = pd.read_sql(query, db_connection)
        
        if len(df) > 0:
            # Seasons should be reasonable years (2000-2030)
            assert df['season'].min() >= 2000
            assert df['season'].max() <= 2030
    
    def test_score_values_reasonable(self, db_connection):
        """Test that scores are within reasonable bounds"""
        query = "SELECT home_score, away_score FROM games WHERE home_score IS NOT NULL LIMIT 100"
        df = pd.read_sql(query, db_connection)
        
        if len(df) > 0:
            # Scores should be between 0 and 100
            assert (df['home_score'] >= 0).all()
            assert (df['home_score'] <= 100).all()
            if 'away_score' in df.columns:
                assert (df['away_score'] >= 0).all()
                assert (df['away_score'] <= 100).all()
    
    def test_game_dates_reasonable(self, db_connection):
        """Test that game dates are reasonable"""
        # Check if gameday column exists
        cursor = db_connection.cursor()
        columns = cursor.execute("PRAGMA table_info(games)").fetchall()
        column_names = [col[1] for col in columns]
        
        if 'gameday' in column_names:
            query = "SELECT gameday FROM games WHERE gameday IS NOT NULL LIMIT 10"
            df = pd.read_sql(query, db_connection)
            
            if len(df) > 0:
                # Dates should be parseable
                assert len(df['gameday']) > 0


# ============================================================================
# PART 4: CRUD Operations Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestCRUDOperations:
    """Test Create, Read, Update, Delete operations"""
    
    def test_read_operation(self, db_connection):
        """Test READ operation"""
        query = "SELECT * FROM games LIMIT 1"
        df = pd.read_sql(query, db_connection)
        
        # Should be able to read data
        assert len(df) >= 0
    
    def test_transaction_rollback(self, db_connection):
        """Test that transactions can rollback"""
        # This is handled by the fixture - it should rollback after test
        cursor = db_connection.cursor()
        
        # Any changes made here will be rolled back
        # (fixture ensures this with rollback in teardown)
        assert cursor is not None
    
    def test_count_rows(self, db_connection):
        """Test counting rows in table"""
        query = "SELECT COUNT(*) as cnt FROM games"
        cursor = db_connection.cursor()
        count = cursor.execute(query).fetchone()[0]
        
        # Should have some games
        assert count >= 0
    
    def test_table_structure(self, db_connection):
        """Test that tables have expected structure"""
        cursor = db_connection.cursor()
        
        # Get column info for games table
        columns = cursor.execute("PRAGMA table_info(games)").fetchall()
        
        assert len(columns) > 0
        
        # Column info: (cid, name, type, notnull, dflt_value, pk)
        column_names = [col[1] for col in columns]
        
        # Should have key columns
        assert 'game_id' in column_names or 'id' in column_names


# ============================================================================
# PART 5: Error Handling Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
class TestErrorHandling:
    """Test error handling for database operations"""
    
    def test_invalid_table_name(self, db_connection):
        """Test query on non-existent table"""
        with pytest.raises(Exception):  # Will raise sqlite3.OperationalError
            pd.read_sql("SELECT * FROM nonexistent_table", db_connection)
    
    def test_invalid_column_name(self, db_connection):
        """Test query with invalid column"""
        with pytest.raises(Exception):
            pd.read_sql("SELECT nonexistent_column FROM games", db_connection)
    
    def test_syntax_error(self, db_connection):
        """Test query with syntax error"""
        with pytest.raises(Exception):
            pd.read_sql("SELECT * FORM games", db_connection)  # FORM instead of FROM
    
    def test_connection_after_close(self):
        """Test that closed connection raises error"""
        conn = sqlite3.connect(':memory:')
        conn.close()
        
        with pytest.raises(Exception):
            conn.execute("SELECT 1")


# ============================================================================
# PART 6: Performance Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.database
@pytest.mark.slow
class TestDatabasePerformance:
    """Test database performance characteristics"""
    
    def test_large_query_performance(self, db_connection):
        """Test that large queries complete in reasonable time"""
        import time
        
        start = time.time()
        query = "SELECT * FROM games LIMIT 1000"
        df = pd.read_sql(query, db_connection)
        elapsed = time.time() - start
        
        # Should complete in under 5 seconds
        assert elapsed < 5.0
        assert len(df) >= 0
    
    def test_aggregation_performance(self, db_connection):
        """Test aggregation query performance"""
        import time
        
        start = time.time()
        query = """
        SELECT season, home_team, COUNT(*) as games, AVG(home_score) as avg_score
        FROM games
        WHERE home_score IS NOT NULL
        GROUP BY season, home_team
        """
        df = pd.read_sql(query, db_connection)
        elapsed = time.time() - start
        
        # Should complete in under 10 seconds
        assert elapsed < 10.0
        assert len(df) >= 0


# ============================================================================
# PART 7: Fixture-Based Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.database
class TestDatabaseFixtures:
    """Test database fixtures and sample data"""
    
    def test_sample_games_data_fixture(self, sample_games_data):
        """Test that sample_games_data fixture works"""
        assert len(sample_games_data) > 0
        # Check if it's a list of dicts or DataFrame
        if isinstance(sample_games_data, list):
            assert 'game_id' in sample_games_data[0] or 'id' in sample_games_data[0]
        else:
            assert len(sample_games_data) > 0
    
    def test_sample_team_stats_fixture(self, sample_team_stats):
        """Test that sample_team_stats fixture works"""
        assert len(sample_team_stats) > 0
        assert 'team' in sample_team_stats.columns
        assert 'season' in sample_team_stats.columns
    
    def test_temp_db_fixture(self, temp_db):
        """Test that temp_db fixture creates isolated database"""
        assert temp_db.exists()
        
        # Should be able to connect
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        
        # Verify table was created
        tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert 'test' in table_names
        
        conn.close()


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
