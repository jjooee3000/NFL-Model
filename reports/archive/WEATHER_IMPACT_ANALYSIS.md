# Weather Impact Analysis (Quick Test)

Workbook: data/nfl_2025_model_data_with_moneylines.xlsx
Train through week: 14
Test weeks: 15+

## Results

- v2 (baseline): Margin MAE 10.261, Total MAE 12.277
- v3 NO weather: Margin MAE 9.770, Total MAE 10.979
- v3 WITH weather: Margin MAE 9.770, Total MAE 10.979

## Interpretation

- Momentum fix in v3 vs v2: +4.8% margin improvement, +10.6% total improvement.
- Weather features (as currently integrated) show no additional improvement over v3 without weather in this quick test.

## Notes

- Weather columns present in games sheet: temp_f, wind_mph, wind_gust_mph, precip_inch, humidity_pct, pressure_hpa
- v3 merges weather directly into feature matrix; no rolling/momentum applied to weather yet.

## Next Steps

1. Outdoor-only analysis: Restrict training/testing to `is_indoor == 0` games.
2. Interaction features: Add simple interactions (e.g., `wind_mph * pass_rate`, `precip_inch * rush_share`).
3. Hyperparameter tuning with weather: Grid-search RF params with weather enabled.
4. Feature importance audit: Confirm whether weather features have near-zero importance.

If you want, I can run the full comparison script to produce a detailed report and try an outdoor-only variant next.
