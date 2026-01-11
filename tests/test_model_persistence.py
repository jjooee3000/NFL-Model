"""Tests for model persistence and registry utilities."""
import pandas as pd
from pathlib import Path
import pytest

from models.model_v3 import NFLHybridModelV3, ModelArtifacts
import utils.model_registry as mr


def _dummy_artifacts():
    return ModelArtifacts(
        features=["f1", "f2"],
        window=8,
        means=pd.Series({"f1": 0.1, "f2": -0.2}),
        sigma_margin=1.0,
        m_margin="margin-model",
        m_total="total-model",
        model_type="randomforest",
        scaler_margin=None,
        scaler_total=None,
        train_date="2026-01-11",
        train_through_week=18,
        data_source="unit-test",
        n_train_samples=10,
        version="v3",
    )


def test_save_and_load_roundtrip(tmp_path: Path):
    """Model save/load should persist artifacts and metadata."""
    model = NFLHybridModelV3(
        workbook_path=str(tmp_path / "dummy.xlsx"),
        window=8,
        model_type="randomforest",
        prefer_sqlite=False,
    )

    artifacts = _dummy_artifacts()
    model._artifacts = artifacts
    model._fit_report = {"n_features": len(artifacts.features), "margin_MAE_test": 1.23}
    model._data_source = "unit-test"
    model._X_cols = artifacts.features

    save_path = tmp_path / "models" / "test_model.pkl"
    saved = model.save_model(path=save_path, metadata={"note": "unit-test"})
    assert saved.exists()

    loaded = NFLHybridModelV3(
        workbook_path=str(tmp_path / "dummy.xlsx"),
        window=8,
        model_type="randomforest",
        prefer_sqlite=False,
    )
    loaded.load_model(saved)

    assert loaded._artifacts.features == artifacts.features
    assert loaded._fit_report.get("margin_MAE_test") == 1.23
    assert loaded._data_source == "unit-test"
    assert loaded._X_cols == artifacts.features


def test_model_registry_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Registry should store and retrieve model metadata."""
    # Redirect registry paths to temp directory
    monkeypatch.setattr(mr, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(mr, "REGISTRY_FILE", tmp_path / "registry.json")
    monkeypatch.setattr(mr, "PROJECT_ROOT", tmp_path)

    model_path = tmp_path / "dummy_model.pkl"
    model_path.write_text("dummy")

    model_id = mr.register_model(
        model_path=model_path,
        model_type="randomforest",
        features_count=2,
        metadata={"mae": 1.0},
    )

    registry = mr.load_registry()
    assert registry["models"], "Registry should contain at least one model entry"

    latest = mr.get_latest_model(model_type="randomforest")
    assert latest == model_path

    info = mr.get_model_info(model_path)
    assert info is not None and info.get("model_id") == model_id

    listed = mr.list_models(model_type="randomforest")
    assert listed and listed[0]["model_id"] == model_id

    removed = mr.delete_model(model_id, remove_file=False)
    assert removed
    assert not mr.list_models(model_type="randomforest")
