"""
Abstract base class for NFL prediction models.

All model versions (v3, v4, etc.) should inherit from this class
to provide a consistent interface for training, prediction, and evaluation.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Tuple, Any, Optional
import pandas as pd


class NFLModel(ABC):
    """
    Abstract base class for NFL prediction models.
    
    Subclasses must implement:
    - load_data()
    - build_features()
    - fit()
    - predict_game()
    """
    
    def __init__(
        self,
        workbook_path: Optional[Path] = None,
        sqlite_path: Optional[Path] = None,
        model_type: str = "randomforest",
    ):
        """
        Initialize model.
        
        Args:
            workbook_path: Path to Excel workbook (fallback data source)
            sqlite_path: Path to SQLite database (primary data source)
            model_type: Type of model ("randomforest", etc.)
        """
        self.workbook_path = workbook_path
        self.sqlite_path = sqlite_path
        self.model_type = model_type
        self._fit_report: Optional[Dict[str, Any]] = None
    
    @abstractmethod
    def load_data(self) -> Tuple[pd.DataFrame, ...]:
        """
        Load training data from Excel or SQLite.
        
        Returns:
            Tuple of DataFrames (implementation-specific)
        """
        pass
    
    @abstractmethod
    def build_features(self, *args, **kwargs) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Build feature matrix and targets.
        
        Returns:
            (X, y_margin, y_total) - feature matrix and targets
        """
        pass
    
    @abstractmethod
    def fit(self, **kwargs) -> Dict[str, Any]:
        """
        Train model on historical data.
        
        Returns:
            Dictionary with fit report (MAE, n_features, etc.)
        """
        pass
    
    @abstractmethod
    def predict_game(self, away_team: str, home_team: str, week: int, **kwargs) -> Dict[str, float]:
        """
        Predict outcome for a single game.
        
        Args:
            away_team: Away team code (e.g., 'CHI')
            home_team: Home team code (e.g., 'GNB')
            week: Week number
        
        Returns:
            Dictionary with predictions:
            - pred_margin_home: predicted margin (home - away)
            - pred_spread_away: implied spread (away perspective)
            - pred_total: predicted total points
            - pred_winprob_home: (optional) win probability
        """
        pass
    
    @property
    def fit_report(self) -> Optional[Dict[str, Any]]:
        """Get last fit report."""
        return self._fit_report


def load_model(
    version: str = "v3",
    workbook_path: Optional[Path] = None,
    sqlite_path: Optional[Path] = None,
    **kwargs
) -> NFLModel:
    """
    Factory function to load a model by version.
    
    Args:
        version: Model version ('v3', 'v4', etc.)
        workbook_path: Path to Excel workbook
        sqlite_path: Path to SQLite database
        **kwargs: Additional arguments passed to model constructor
    
    Returns:
        Initialized model instance
    
    Example:
        model = load_model('v3')
        model.fit(train_through_week=14)
        pred = model.predict_game('CHI', 'GNB', week=1)
    """
    if version == "v3":
        from models.model_v3 import NFLHybridModelV3
        return NFLHybridModelV3(
            workbook_path=workbook_path or "data/nfl_2025_model_data_with_moneylines.xlsx",
            **kwargs
        )
    elif version == "v4":
        from models.model_v4 import NFLModelV4
        return NFLModelV4(
            workbook_path=workbook_path,
            sqlite_path=sqlite_path or Path("data/nfl_model.db"),
            **kwargs
        )
    else:
        raise ValueError(f"Unknown model version: {version}. Supported: v3, v4")


__all__ = ["NFLModel", "load_model"]
