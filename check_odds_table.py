"""Check if odds table exists and what it contains"""
import sqlite3

conn = sqlite3.connect('data/nfl_model.db')

# Check if odds table exists
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Available tables:")
for table in tables:
    print(f"  - {table[0]}")

# Check if odds table exists
if ('odds',) in tables:
    print("\n✓ 'odds' table exists")
    
    # Check schema
    schema = conn.execute("PRAGMA table_info(odds)").fetchall()
    print("\nOdds table schema:")
    for col in schema:
        print(f"  {col[1]}: {col[2]}")
    
    # Check data
    count = conn.execute("SELECT COUNT(*) FROM odds").fetchone()[0]
    print(f"\nRows in odds table: {count}")
    
    if count > 0:
        sample = conn.execute("SELECT * FROM odds LIMIT 3").fetchall()
        print("\nSample data:")
        for row in sample:
            print(f"  {row}")
else:
    print("\n✗ 'odds' table does NOT exist")
    print("\nThe model expects an 'odds' table but we added columns to 'games' table instead.")
    print("We have two options:")
    print("  1. Create a separate 'odds' table (more normalized)")
    print("  2. Modify model to read odds from 'games' table columns (simpler)")

conn.close()
