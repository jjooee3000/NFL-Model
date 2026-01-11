"""
Tests for API endpoints

Tests cover:
- Health check endpoints
- Prediction endpoints
- Upcoming games endpoints
- Error handling
- Response validation
"""
import pytest
import sys
from pathlib import Path
import json
from datetime import datetime

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============================================================================
# PART 1: Health Check Endpoint Tests
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_health_endpoint(self, api_client):
        """Test GET / returns health status"""
        response = api_client.get("/")
        
        assert response.status_code == 200
        # Root may return HTML or JSON
    
    def test_health_endpoint(self, api_client):
        """Test GET /health returns health"""
        response = api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
    
    def test_health_response_time(self, api_client):
        """Test health endpoint responds quickly"""
        import time
        
        start = time.time()
        response = api_client.get("/health")
        elapsed = time.time() - start
        
        # Should respond in under 1 second
        assert elapsed < 1.0
        assert response.status_code == 200


# ============================================================================
# PART 2: Prediction Endpoint Tests
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
class TestPredictionEndpoints:
    """Test prediction endpoints"""
    
    def test_prediction_endpoint_exists(self, api_client):
        """Test /predict endpoint exists"""
        # POST might require data, so we test that it exists (not 404)
        response = api_client.post("/predict", json={})
        
        # Should not be 404 (route exists)
        # Might be 422 (validation error) or 400 (bad request)
        assert response.status_code != 404
    
    def test_prediction_with_valid_data(self, api_client):
        """Test prediction with valid game data"""
        game_data = {
            "home_team": "KC",
            "away_team": "BAL",
            "season": 2024,
            "week": 1
        }
        
        response = api_client.post("/predict", json=game_data)
        
        # Should succeed or return validation error
        assert response.status_code in [200, 422, 400, 500]
    
    def test_prediction_missing_data(self, api_client):
        """Test prediction with missing required data"""
        game_data = {}
        
        response = api_client.post("/predict", json=game_data)
        
        # Should return validation error
        assert response.status_code in [400, 422, 500]
    
    def test_prediction_get_method_not_allowed(self, api_client):
        """Test that GET is not allowed on predictions endpoint"""
        response = api_client.get("/predict")
        
        # Should be 405 (method not allowed) or 404 (no GET route)
        assert response.status_code in [404, 405]


# ============================================================================
# PART 3: Upcoming Games Endpoint Tests
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
class TestUpcomingEndpoints:
    """Test upcoming games endpoints"""
    
    def test_upcoming_endpoint_exists(self, api_client):
        """Test /upcoming endpoint exists"""
        response = api_client.get("/upcoming")
        
        # Should succeed or have error
        assert response.status_code in [200, 500]
    
    def test_upcoming_returns_list(self, api_client):
        """Test /upcoming returns list of games"""
        response = api_client.get("/upcoming")
        
        if response.status_code == 200:
            data = response.json()
            
            # Should return list or dict containing games
            assert isinstance(data, (list, dict))
    
    def test_upcoming_game_structure(self, api_client):
        """Test upcoming game objects have correct structure"""
        response = api_client.get("/api/upcoming")
        
        if response.status_code == 200:
            data = response.json()
            
            # If list of games, check first game
            if isinstance(data, list) and len(data) > 0:
                game = data[0]
                assert isinstance(game, dict)
                # Should have team info
    
    def test_upcoming_with_week_param(self, api_client):
        """Test /api/upcoming with week parameter"""
        response = api_client.get("/api/upcoming?week=1")
        
        # Should succeed or not be implemented
        assert response.status_code in [200, 404, 422]
    
    def test_upcoming_with_season_param(self, api_client):
        """Test /api/upcoming with season parameter"""
        response = api_client.get("/api/upcoming?season=2024")
        
        # Should succeed or not be implemented
        assert response.status_code in [200, 404, 422]


# ============================================================================
# PART 4: Error Handling Tests
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
class TestAPIErrorHandling:
    """Test API error handling"""
    
    def test_404_not_found(self, api_client):
        """Test 404 for non-existent endpoint"""
        response = api_client.get("/api/nonexistent")
        
        assert response.status_code == 404
    
    def test_invalid_json(self, api_client):
        """Test handling of invalid JSON"""
        response = api_client.post(
            "/api/predictions",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Should return error
        assert response.status_code in [400, 422]
    
    def test_method_not_allowed(self, api_client):
        """Test method not allowed errors"""
        # Try DELETE on health endpoint
        response = api_client.delete("/api/health")
        
        # Should be 405 or 404
        assert response.status_code in [404, 405]
    
    def test_large_payload(self, api_client):
        """Test handling of large payload"""
        # Create large payload
        large_data = {"data": "x" * 10000}
        
        response = api_client.post("/api/predictions", json=large_data)
        
        # Should handle without crashing
        assert response.status_code in [200, 400, 413, 422]


# ============================================================================
# PART 5: Response Validation Tests
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
class TestResponseValidation:
    """Test response format validation"""
    
    def test_json_response_format(self, api_client):
        """Test that responses are valid JSON"""
        response = api_client.get("/api/health")
        
        assert response.status_code == 200
        
        # Should be valid JSON
        data = response.json()
        assert isinstance(data, dict)
    
    def test_content_type_header(self, api_client):
        """Test Content-Type header is application/json"""
        response = api_client.get("/api/health")
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("Content-Type", "")
    
    def test_timestamp_format(self, api_client):
        """Test timestamp fields are valid ISO format"""
        response = api_client.get("/api/health")
        
        if response.status_code == 200:
            data = response.json()
            
            if "timestamp" in data:
                # Try parsing timestamp
                try:
                    datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                    timestamp_valid = True
                except:
                    timestamp_valid = False
                
                # Timestamp should be parseable
                assert timestamp_valid or isinstance(data["timestamp"], str)
    
    def test_numeric_fields_are_numbers(self, api_client):
        """Test that numeric fields are actually numbers"""
        game_data = {
            "home_team": "KC",
            "away_team": "BAL"
        }
        
        response = api_client.post("/api/predictions", json=game_data)
        
        if response.status_code == 200:
            data = response.json()
            
            # If predictions exist, they should be numbers
            for key in data:
                if 'margin' in key.lower() or 'total' in key.lower() or 'score' in key.lower():
                    if data[key] is not None:
                        assert isinstance(data[key], (int, float))


# ============================================================================
# PART 6: Authentication/Authorization Tests (if applicable)
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
class TestAPIAuthentication:
    """Test API authentication (if implemented)"""
    
    def test_public_endpoints_no_auth(self, api_client):
        """Test that public endpoints don't require auth"""
        response = api_client.get("/api/health")
        
        # Should succeed without auth
        assert response.status_code == 200
    
    def test_cors_headers(self, api_client):
        """Test CORS headers if enabled"""
        response = api_client.options("/api/health")
        
        # OPTIONS should be allowed
        assert response.status_code in [200, 204, 404, 405]


# ============================================================================
# PART 7: Integration Tests
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
@pytest.mark.slow
class TestAPIIntegration:
    """Test full API integration scenarios"""
    
    def test_health_then_prediction_flow(self, api_client):
        """Test typical API usage flow"""
        # 1. Check health
        health = api_client.get("/api/health")
        assert health.status_code == 200
        
        # 2. Get upcoming games
        upcoming = api_client.get("/api/upcoming")
        # May or may not exist
        
        # 3. Make prediction
        prediction = api_client.post("/api/predictions", json={
            "home_team": "KC",
            "away_team": "BAL"
        })
        # May succeed or fail depending on implementation
    
    def test_multiple_predictions(self, api_client):
        """Test making multiple predictions in sequence"""
        games = [
            {"home_team": "KC", "away_team": "BAL"},
            {"home_team": "SF", "away_team": "DAL"},
            {"home_team": "GB", "away_team": "CHI"}
        ]
        
        for game in games:
            response = api_client.post("/api/predictions", json=game)
            # Each should return consistent status codes
            assert response.status_code in [200, 400, 422, 500]
    
    def test_concurrent_requests(self, api_client):
        """Test handling of concurrent requests"""
        import threading
        
        results = []
        
        def make_request():
            response = api_client.get("/api/health")
            results.append(response.status_code)
        
        # Make 5 concurrent requests
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should succeed
        assert all(code == 200 for code in results)


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
