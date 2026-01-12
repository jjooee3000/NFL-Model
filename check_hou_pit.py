import sqlite3
conn = sqlite3.connect('data/nfl_model.db')
cursor = conn.cursor()
cursor.execute('''SELECT game_id, away_team, home_team, week, home_score, away_score 
FROM games 
WHERE (home_team = "HOU" OR away_team = "HOU" OR home_team = "PIT" OR away_team = "PIT") 
AND week >= 19 
ORDER BY week''')
games = cursor.fetchall()
print('HOU/PIT games week 19+:')
for g in games:
    print(f'{g[0]}: {g[1]} @ {g[2]} (Week {g[3]}) - Scores: {g[4]}/{g[5]}')
conn.close()
