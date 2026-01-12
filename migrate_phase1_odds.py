"""
Phase 1 Database Migration: Add ESPN API enrichment columns
Adds betting lines, team records, attendance, and broadcast data
"""
import sqlite3
from pathlib import Path

DB_PATH = Path('data/nfl_model.db')

def add_phase1_columns():
    """Add Phase 1 enrichment columns to games table"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Define new columns to add
    new_columns = {
        # Betting Lines (from ESPN odds)
        'odds_spread': 'REAL',  # Closing spread (negative = home favored)
        'odds_total': 'REAL',  # Closing over/under total
        'odds_moneyline_home': 'TEXT',  # e.g., "+130"
        'odds_moneyline_away': 'TEXT',  # e.g., "-155"
        'odds_open_spread': 'REAL',  # Opening spread for line movement tracking
        'odds_open_total': 'REAL',  # Opening total
        'odds_provider': 'TEXT',  # Sportsbook name (e.g., "Draft Kings")
        'odds_timestamp': 'TIMESTAMP',  # When odds were fetched
        
        # Team Records (from ESPN records)
        'home_record_wins': 'INTEGER',
        'home_record_losses': 'INTEGER',
        'away_record_wins': 'INTEGER',
        'away_record_losses': 'INTEGER',
        
        # Game Context
        'attendance': 'INTEGER',
        'broadcast_network': 'TEXT',  # e.g., "NBC", "FOX", "CBS"
        'broadcast_primetime': 'INTEGER',  # 1 if primetime (SNF, MNF, TNF), 0 otherwise
    }
    
    # Check existing columns
    existing_cols = [row[1] for row in cursor.execute('PRAGMA table_info(games)')]
    
    # Add each new column if it doesn't exist
    added = []
    skipped = []
    
    for col_name, col_type in new_columns.items():
        if col_name in existing_cols:
            skipped.append(col_name)
        else:
            try:
                cursor.execute(f'ALTER TABLE games ADD COLUMN {col_name} {col_type}')
                added.append(col_name)
                print(f"✓ Added column: {col_name} ({col_type})")
            except sqlite3.OperationalError as e:
                print(f"✗ Error adding {col_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\nMigration Summary:")
    print(f"  Added: {len(added)} columns")
    print(f"  Skipped (already exist): {len(skipped)} columns")
    
    if added:
        print(f"\n✓ Database schema updated successfully!")
    else:
        print(f"\n⚠ No changes needed - all columns already exist")
    
    return added, skipped

if __name__ == '__main__':
    print("="*80)
    print("PHASE 1 DATABASE MIGRATION: ESPN API Enrichment")
    print("="*80)
    print("\nAdding columns for:")
    print("  - Betting lines (spread, total, moneyline)")
    print("  - Team records (wins/losses)")
    print("  - Attendance and broadcast info")
    print()
    
    added, skipped = add_phase1_columns()
