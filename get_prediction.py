import sqlite3
conn = sqlite3.connect('data/nfl_model.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM ensemble_predictions WHERE (away_team='HOU' AND home_team='PIT') ORDER BY timestamp DESC LIMIT 1")
row = cursor.fetchone()
cursor.execute("PRAGMA table_info(ensemble_predictions)")
cols = [c[1] for c in cursor.fetchall()]
print('Columns:', cols)
print('\nLatest HOU@PIT prediction:')
if row:
    pred = dict(zip(cols, row))
    for k, v in pred.items():
        print(f"  {k}: {v}")
conn.close()
