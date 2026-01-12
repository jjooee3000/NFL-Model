import sqlite3
conn = sqlite3.connect("data/nfl_model.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(team_games)")
cols = cursor.fetchall()
print(f"Total columns: {len(cols)}")
print("\nColumns:")
for i, col in enumerate(cols, 1):
    print(f"{i:2d}. {col[1]}")
conn.close()
