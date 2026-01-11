"""Quick test to verify weather features are working and measure basic impact."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from models.model_v3 import NFLHybridModelV3

# Paths
workbook_path = Path(__file__).parent.parent.parent / "data" / "nfl_2025_model_data_with_moneylines.xlsx"

# Load data
print("Loading data...")
games_df = pd.read_excel(workbook_path, sheet_name='games')
team_games_df = pd.read_excel(workbook_path, sheet_name='team_games')
odds_df = pd.read_excel(workbook_path, sheet_name='odds')

# Check weather columns
weather_cols = ['temp_f', 'wind_mph', 'wind_gust_mph', 'precip_inch', 'humidity_pct', 'pressure_hpa']
available_weather = [col for col in weather_cols if col in games_df.columns]
print(f"\nWeather columns available: {available_weather}")
print(f"Sample weather data (first 5 games):")
print(games_df[['away_team', 'home_team'] + available_weather].head())

# Train/test split
train_week = 14
test_games = games_df[games_df['week'] > train_week].copy()

print(f"\nTrain through week: {train_week}")
print(f"Test: {len(test_games)} games (weeks 15+)")

# Train model
print("\nTraining v3 with weather features...")
model = NFLHybridModelV3(workbook_path)
result = model.fit(train_through_week=train_week, return_predictions=True)

# Extract test performance from report
margin_mae = result['margin_MAE_test']
total_mae = result['total_MAE_test']
n_features = result['n_features']
n_train = result['n_train_games']
n_test = result['n_test_games']

print(f"\n{'='*60}")
print(f"RESULTS: v3 with weather")
print(f"{'='*60}")
print(f"Features: {n_features}")
print(f"Train games: {n_train}, Test games: {n_test}")
print(f"Margin MAE: {margin_mae:.3f}")
print(f"Total MAE:  {total_mae:.3f}")
print(f"{'='*60}")
