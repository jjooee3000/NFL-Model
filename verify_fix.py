"""Verify the Recent Predictions & Accuracy section is fixed"""
import requests
import time

print("="*80)
print("TESTING RECENT PREDICTIONS & ACCURACY FIX")
print("="*80)

# Give server a moment to fully start
time.sleep(2)

# Test the homepage
print("\nFetching homepage data...")
r = requests.get('http://127.0.0.1:8083/', timeout=5)

if r.status_code == 200:
    print(f"✓ Status: {r.status_code}")
    
    # Check if LAC@NE appears in the response
    content = r.text
    lac_ne_count = content.count('LAC@NE')
    
    print(f"\nSearching for 'LAC@NE' in Recent Predictions section...")
    print(f"Found 'LAC@NE' {lac_ne_count} times in HTML")
    
    # Look for the table section
    if 'Recent Predictions & Accuracy' in content:
        print("✓ Found 'Recent Predictions & Accuracy' section")
        
        # Count table rows in that section
        import re
        # Extract the section between Recent Predictions and the next section
        match = re.search(r'Recent Predictions & Accuracy.*?</table>', content, re.DOTALL)
        if match:
            section = match.group(0)
            row_count = section.count('<tr class=')
            print(f"✓ Table has {row_count} data rows")
            
            # Check for LAC@NE specifically in this section
            lac_in_section = section.count('LAC')
            print(f"✓ LAC appears {lac_in_section} times in this section (should be 0)")
            
            # Extract game IDs from the section
            game_ids = re.findall(r'(20\d{2}_W\d+_[A-Z]{3}_[A-Z]{3})', section)
            print(f"\nGames shown:")
            for i, gid in enumerate(set(game_ids), 1):
                count = game_ids.count(gid)
                print(f"  {i}. {gid} - appears {count} time(s) {'✓' if count == 1 else '✗ DUPLICATE!'}")
    else:
        print("✗ Could not find 'Recent Predictions & Accuracy' section")
else:
    print(f"✗ Error: Status {r.status_code}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("✓ LAC@NE (today's ongoing game) should NOT appear in Recent Predictions")
print("✓ Each game should appear exactly ONCE (no duplicates)")
print("="*80)
