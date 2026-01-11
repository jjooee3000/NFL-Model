import sqlite3

conn = sqlite3.connect('data/nfl_model.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

print('\n' + '='*100)
print('DATABASE SCHEMA AUDIT - What Data We Currently Have')
print('='*100 + '\n')

total_cols = 0
for table in tables:
    cursor.execute(f'PRAGMA table_info({table})')
    cols = cursor.fetchall()
    col_count = len(cols)
    total_cols += col_count
    
    # Get row count
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    row_count = cursor.fetchone()[0]
    
    col_names = [col[1] for col in cols]
    print(f'{table:40} | Rows: {row_count:6} | Cols: {col_count:2}')
    for i, col_name in enumerate(col_names, 1):
        if i <= 10:
            print(f'  {i:2}. {col_name}')
    if col_count > 10:
        print(f'  ... and {col_count - 10} more')
    print()

print(f'TOTAL: {len(tables)} tables, {total_cols} columns')
conn.close()
