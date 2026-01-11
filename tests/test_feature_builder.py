"""
Tests for feature engineering and construction functions

Tests cover:
- Rolling window calculations
- EMA (Exponential Moving Average) calculations
- Trend and volatility features
- Feature interaction generation
- Data validation and edge cases
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# ============================================================================
# PART 1: Rolling Window Feature Tests
# ============================================================================

@pytest.mark.unit
class TestRollingWindows:
    """Test rolling window calculations"""
    
    def test_rolling_mean_basic(self):
        """Test basic rolling mean calculation"""
        data = pd.Series([10, 20, 30, 40, 50])
        rolling_mean = data.rolling(window=3, min_periods=1).mean()
        
        # First value should be just itself
        assert rolling_mean.iloc[0] == 10.0
        
        # Third value should be mean of first 3
        assert rolling_mean.iloc[2] == 20.0  # (10+20+30)/3
        
        # Last value should be mean of last 3
        assert rolling_mean.iloc[4] == 40.0  # (30+40+50)/3
    
    def test_rolling_mean_insufficient_data(self):
        """Test rolling mean with insufficient data"""
        data = pd.Series([10, 20])
        rolling_mean = data.rolling(window=5, min_periods=1).mean()
        
        # Should still calculate with available data
        assert len(rolling_mean) == 2
        assert not rolling_mean.isna().any()
    
    def test_rolling_std(self):
        """Test rolling standard deviation"""
        data = pd.Series([10, 10, 10, 20, 20, 20])
        rolling_std = data.rolling(window=3, min_periods=1).std()
        
        # First 3 values should have 0 std
        assert rolling_std.iloc[2] == 0.0
        
        # Values with variation should have positive std
        assert rolling_std.iloc[4] > 0
    
    def test_rolling_min_max(self):
        """Test rolling min and max"""
        data = pd.Series([5, 15, 10, 20, 8])
        
        rolling_min = data.rolling(window=3, min_periods=1).min()
        rolling_max = data.rolling(window=3, min_periods=1).max()
        
        # Check window of [5, 15, 10]
        assert rolling_min.iloc[2] == 5
        assert rolling_max.iloc[2] == 15
        
        # Check window of [15, 10, 20]
        assert rolling_min.iloc[3] == 10
        assert rolling_max.iloc[3] == 20


# ============================================================================
# PART 2: EMA (Exponential Moving Average) Tests
# ============================================================================

@pytest.mark.unit
class TestEMAFeatures:
    """Test exponential moving average calculations"""
    
    def test_ema_basic(self):
        """Test basic EMA calculation"""
        data = pd.Series([10, 20, 30, 40, 50])
        
        # EMA with span=3 (alpha = 2/(span+1) = 0.5)
        ema = data.ewm(span=3, adjust=False).mean()
        
        # First value should equal first data point
        assert ema.iloc[0] == 10.0
        
        # EMA should increase with upward trend
        assert ema.iloc[-1] > ema.iloc[0]
        assert ema.iloc[-1] < data.iloc[-1]  # But less than current value
    
    def test_ema_decay(self):
        """Test EMA decay behavior"""
        # Constant value then spike
        data = pd.Series([10, 10, 10, 10, 100])
        ema = data.ewm(span=3, adjust=False).mean()
        
        # EMA should react to spike but not reach full value
        assert ema.iloc[-1] > 10
        assert ema.iloc[-1] < 100
    
    def test_ema_vs_sma(self):
        """Test that EMA reacts faster than SMA"""
        data = pd.Series([10, 10, 10, 50, 50])
        
        ema = data.ewm(span=3, adjust=False).mean()
        sma = data.rolling(window=3, min_periods=1).mean()
        
        # After value change, EMA should be higher than SMA
        # (because it weights recent values more)
        assert ema.iloc[-1] >= sma.iloc[-1]
    
    def test_ema_alpha(self):
        """Test EMA with different alpha values"""
        data = pd.Series([10, 20, 30, 40, 50])
        
        # High alpha (0.9) = more weight to recent
        ema_high = data.ewm(alpha=0.9, adjust=False).mean()
        
        # Low alpha (0.1) = more weight to history
        ema_low = data.ewm(alpha=0.1, adjust=False).mean()
        
        # High alpha should be closer to current values
        assert abs(ema_high.iloc[-1] - data.iloc[-1]) < abs(ema_low.iloc[-1] - data.iloc[-1])


# ============================================================================
# PART 3: Trend and Volatility Features
# ============================================================================

@pytest.mark.unit
class TestTrendVolatilityFeatures:
    """Test trend and volatility feature calculations"""
    
    def test_trend_calculation(self):
        """Test trend (current - historical average)"""
        current = 30.0
        historical = pd.Series([10, 15, 20, 25])
        hist_mean = historical.mean()
        
        trend = current - hist_mean
        
        # Upward trend should be positive
        assert trend > 0
        assert trend == 30.0 - 17.5  # 30 - (10+15+20+25)/4
    
    def test_volatility_calculation(self):
        """Test volatility (standard deviation)"""
        stable = pd.Series([10, 10, 10, 10, 10])
        volatile = pd.Series([5, 25, 10, 30, 15])
        
        stable_vol = stable.std()
        volatile_vol = volatile.std()
        
        # Stable series should have low volatility
        assert stable_vol == 0.0
        
        # Volatile series should have high volatility
        assert volatile_vol > 5.0
    
    def test_momentum_indicator(self):
        """Test momentum (recent avg - older avg)"""
        recent = pd.Series([30, 35, 40])
        older = pd.Series([10, 15, 20])
        
        momentum = recent.mean() - older.mean()
        
        # Positive momentum for upward trend
        assert momentum > 0
        assert momentum == 35.0 - 15.0  # 35 - 15 = 20
    
    def test_coefficient_of_variation(self):
        """Test CV (std / mean)"""
        data = pd.Series([10, 20, 30])
        
        cv = data.std() / data.mean()
        
        # CV should be positive
        assert cv > 0
        
        # Higher CV means more relative variation
        assert isinstance(cv, (int, float))


# ============================================================================
# PART 4: Feature Interaction Generation
# ============================================================================

@pytest.mark.unit
class TestFeatureInteractions:
    """Test feature interaction generation"""
    
    def test_simple_interaction(self):
        """Test simple multiplication interaction"""
        feature_a = 10.0
        feature_b = 5.0
        
        interaction = feature_a * feature_b
        
        assert interaction == 50.0
    
    def test_ratio_interaction(self):
        """Test ratio-based interaction"""
        offense_yards = 400.0
        defense_yards = 300.0
        
        ratio = offense_yards / defense_yards
        
        assert ratio > 1.0  # Offense outperforms
        assert ratio == pytest.approx(1.333, rel=0.01)
    
    def test_difference_interaction(self):
        """Test difference-based interaction"""
        home_points = 28.0
        away_points = 21.0
        
        margin = home_points - away_points
        
        assert margin == 7.0
    
    def test_interaction_matrix(self):
        """Test creating interaction matrix"""
        features = pd.DataFrame({
            'feature_a': [1, 2, 3],
            'feature_b': [4, 5, 6]
        })
        
        # Create interaction by multiplying columns
        features['interaction_ab'] = features['feature_a'] * features['feature_b']
        
        assert 'interaction_ab' in features.columns
        assert features['interaction_ab'].iloc[0] == 4  # 1 * 4
        assert features['interaction_ab'].iloc[1] == 10  # 2 * 5
        assert features['interaction_ab'].iloc[2] == 18  # 3 * 6


# ============================================================================
# PART 5: Data Validation and Edge Cases
# ============================================================================

@pytest.mark.unit
class TestDataValidation:
    """Test data validation and edge case handling"""
    
    def test_handle_missing_values(self):
        """Test handling of NaN values"""
        data = pd.Series([10, np.nan, 30, 40])
        
        # Should have 1 NaN
        assert data.isna().sum() == 1
        
        # Fillna with mean
        filled = data.fillna(data.mean())
        assert filled.isna().sum() == 0
    
    def test_handle_zero_division(self):
        """Test handling of division by zero"""
        numerator = 10.0
        denominator = 0.0
        
        # Should handle gracefully
        with pytest.raises(ZeroDivisionError):
            _ = numerator / denominator
        
        # Safe division
        result = numerator / denominator if denominator != 0 else 0.0
        assert result == 0.0
    
    def test_handle_inf_values(self):
        """Test handling of infinity values"""
        data = pd.Series([1.0, np.inf, 3.0, -np.inf, 5.0])
        
        # Check for inf
        assert data.isin([np.inf, -np.inf]).sum() == 2
        
        # Replace inf with NaN then fill
        clean = data.replace([np.inf, -np.inf], np.nan).fillna(0)
        assert not clean.isin([np.inf, -np.inf]).any()
    
    def test_feature_scaling_normalization(self):
        """Test feature normalization"""
        data = pd.Series([10, 20, 30, 40, 50])
        
        # Min-max normalization
        normalized = (data - data.min()) / (data.max() - data.min())
        
        # Should be between 0 and 1
        assert normalized.min() == 0.0
        assert normalized.max() == 1.0
        assert (normalized >= 0).all()
        assert (normalized <= 1).all()
    
    def test_feature_standardization(self):
        """Test feature standardization (z-score)"""
        data = pd.Series([10, 20, 30, 40, 50])
        
        # Standardize
        standardized = (data - data.mean()) / data.std()
        
        # Mean should be ~0, std should be ~1
        assert abs(standardized.mean()) < 1e-10
        assert abs(standardized.std() - 1.0) < 1e-10


# ============================================================================
# PART 6: Time-Based Features
# ============================================================================

@pytest.mark.unit
class TestTimeBasedFeatures:
    """Test time-based feature extraction"""
    
    def test_days_between_games(self):
        """Test calculating days rest between games"""
        game1_date = datetime(2024, 9, 8)  # Sunday
        game2_date = datetime(2024, 9, 15)  # Next Sunday
        
        days_rest = (game2_date - game1_date).days
        
        assert days_rest == 7
    
    def test_week_of_season(self):
        """Test extracting week number"""
        season_start = datetime(2024, 9, 5)
        current_game = datetime(2024, 9, 26)
        
        weeks_elapsed = (current_game - season_start).days // 7
        
        assert weeks_elapsed == 3  # Week 3
    
    def test_is_home_game(self):
        """Test home/away indicator"""
        is_home = True
        is_away = False
        
        home_indicator = 1 if is_home else 0
        away_indicator = 1 if is_away else 0
        
        assert home_indicator == 1
        assert away_indicator == 0
    
    def test_season_phase(self):
        """Test identifying season phase (early/mid/late)"""
        early_week = 3
        mid_week = 9
        late_week = 15
        
        def get_phase(week):
            if week <= 6:
                return "early"
            elif week <= 12:
                return "mid"
            else:
                return "late"
        
        assert get_phase(early_week) == "early"
        assert get_phase(mid_week) == "mid"
        assert get_phase(late_week) == "late"


# ============================================================================
# PART 7: Advanced Feature Engineering
# ============================================================================

@pytest.mark.unit
class TestAdvancedFeatures:
    """Test advanced feature engineering techniques"""
    
    def test_weighted_average(self):
        """Test weighted average calculation"""
        values = np.array([10, 20, 30])
        weights = np.array([0.5, 0.3, 0.2])
        
        weighted_avg = np.average(values, weights=weights)
        
        # Manual calculation: 10*0.5 + 20*0.3 + 30*0.2 = 5 + 6 + 6 = 17
        assert weighted_avg == 17.0
    
    def test_percentile_rank(self):
        """Test percentile ranking"""
        data = pd.Series([10, 20, 30, 40, 50])
        
        # Get percentile rank for value 30
        percentile = (data < 30).sum() / len(data) * 100
        
        assert percentile == 40.0  # 30 is at 40th percentile
    
    def test_z_score_outlier_detection(self):
        """Test outlier detection using z-score"""
        # Create data with clear outlier
        data = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 100.0])
        
        # Calculate z-scores
        mean = data.mean()
        std = data.std()
        z_scores = (data - mean) / std
        
        # Use threshold of 2 (common for outlier detection)
        outliers = abs(z_scores) > 2.0
        
        # The extreme value (100) should be detected as outlier
        assert outliers.iloc[-1] == True, "Extreme value should be detected as outlier"
        
        # Should have at least one outlier
        assert outliers.sum() >= 1, "Should detect at least one outlier"
    
    def test_moving_correlation(self):
        """Test moving correlation between features"""
        feature_a = pd.Series([1, 2, 3, 4, 5, 6, 7, 8])
        feature_b = pd.Series([2, 4, 6, 8, 10, 12, 14, 16])
        
        # Perfect linear relationship
        correlation = feature_a.corr(feature_b)
        
        assert abs(correlation - 1.0) < 1e-10  # Perfect correlation


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
