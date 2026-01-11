# ESPN API Integration Analysis

**Date**: 2026-01-11  
**Purpose**: Evaluate ESPN API capabilities and integration with NFL Model project  
**Status**: ✅ **HIGHLY RECOMMENDED** - ESPN API is comprehensive and already partially integrated

---

## Executive Summary

**Recommendation**: **ADOPT ESPN API as primary data source**

The ESPN API (`site.api.espn.com`) provides comprehensive, structured, real-time NFL data that perfectly aligns with your project needs. Your codebase **already uses ESPN API** in [src/utils/upcoming_games.py](src/utils/upcoming_games.py), and it can be expanded to replace or supplement other data sources.

**Key Benefits**:
- ✅ **Free, public API** - No authentication required
- ✅ **Real-time data** - Live scores, weather, game status
- ✅ **Comprehensive** - Games, teams, standings, schedules
- ✅ **Well-structured JSON** - Easy to parse and integrate
- ✅ **Historical access** - Query by date, week, season
- ✅ **Already integrated** - Your project already uses it

---

## ESPN API Capabilities

### Base URL
```
http://site.api.espn.com/apis/site/v2/sports/football/nfl
```

### Available Endpoints

#### 1. **Scoreboard** - Games and Scores
**Endpoint**: `/scoreboard`

**Parameters**:
- `dates=YYYYMMDD` - Specific date (e.g., `20260111`)
- `week=N` - Week number (1-18)
- `seasontype=N` - Season type (1=preseason, 2=regular, 3=playoffs)

**Data Provided**:
- ✅ Game ID
- ✅ Date/Time
- ✅ Home/Away teams (with abbreviations)
- ✅ Scores (live and final)
- ✅ Game status (scheduled, in-progress, final)
- ✅ **Weather data** (temperature, conditions, wind)
- ✅ Odds (when available)
- ✅ Links to detailed stats

**Example Response**:
```json
{
  "week": {"number": 1},
  "season": {"type": 3},
  "events": [
    {
      "id": "401772977",
      "date": "2026-01-11T18:00Z",
      "name": "Jacksonville Jaguars at Buffalo Bills",
      "weather": {
        "temperature": 32,
        "conditionId": "1",
        "link": {...}
      },
      "competitions": [
        {
          "competitors": [
            {
              "team": {"abbreviation": "JAX"},
              "homeAway": "away",
              "score": "7"
            },
            {
              "team": {"abbreviation": "BUF"},
              "homeAway": "home",
              "score": "13"
            }
          ],
          "status": {
            "type": {"name": "STATUS_IN_PROGRESS"}
          }
        }
      ]
    }
  ]
}
```

---

#### 2. **Teams** - Team Information
**Endpoint**: `/teams`

**Data Provided**:
- ✅ All 32 NFL teams
- ✅ Team abbreviations (for matching)
- ✅ Full names, colors, logos
- ✅ Links to team pages

**Use Cases**:
- Team name standardization
- Logo/branding for UI
- Team metadata

---

#### 3. **Standings** - Season Standings
**Endpoint**: `/standings`

**Data Provided**:
- ✅ Division standings
- ✅ Win-loss records
- ✅ Playoff positioning

**Use Cases**:
- Team strength features
- Playoff probability
- Contextual analysis

---

### Advanced Query Capabilities

**Query by specific date**:
```
/scoreboard?dates=20260111
```

**Query by week and season type**:
```
/scoreboard?week=18&seasontype=2
```

**Query multiple dates** (for backfilling):
```python
# Loop through dates
for date in date_range:
    url = f"{base}/scoreboard?dates={date.strftime('%Y%m%d')}"
```

---

## Current Integration Status

### Already Implemented ✅

**File**: [src/utils/upcoming_games.py](src/utils/upcoming_games.py)

**Function**: `fetch_espn_upcoming(days_ahead=7)`
- Uses ESPN scoreboard API
- Fetches upcoming games
- Handles regular season and playoffs
- Deduplicates results
- Filters for scheduled games only

**Code**:
```python
API_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

def fetch_espn_upcoming(days_ahead: int = 7) -> List[Dict[str, Any]]:
    for season_type in [2, 3]:  # Regular + Playoffs
        for i in range(days_ahead + 1):
            date = today + timedelta(days=i)
            params = {
                "dates": date.strftime("%Y%m%d"),
                "seasontype": str(season_type)
            }
            resp = requests.get(API_URL, params=params, timeout=10)
            # Parse events...
```

### Other ESPN Usage in Codebase

**Files using ESPN API**:
1. [src/utils/upcoming_games.py](src/utils/upcoming_games.py) - Upcoming games
2. [src/utils/schedule.py](src/utils/schedule.py) - Schedule fetching
3. [src/models/archive/model_v0.py](src/models/archive/model_v0.py) - Historical usage
4. [test_espn.py](test_espn.py) - API testing
5. [test_espn_api.py](test_espn_api.py) - API exploration

---

## Gaps in Current Implementation

### What ESPN Provides That You're NOT Using

1. **Weather Data** ⚠️ CRITICAL
   - Available in game events
   - Currently you scrape weather from external sources
   - **Recommendation**: Extract from ESPN API directly

2. **Odds Data** ⚠️ MEDIUM
   - Sometimes available in competition objects
   - You use separate odds sources
   - **Recommendation**: Use as supplementary source

3. **Live Game Status** ⚠️ MEDIUM
   - In-progress scores
   - Quarter/time remaining
   - **Recommendation**: Add for live prediction updates

4. **Historical Game Stats** ⚠️ LOW
   - Links to detailed statistics
   - Box scores available via links
   - **Recommendation**: Explore for richer features

---

## Recommended Enhancements

### Priority 1: Weather Integration ⭐⭐⭐
**Current**: Scraping weather from external sources  
**Improvement**: Extract weather from ESPN game events

**Benefits**:
- More reliable (same source as game data)
- No separate API calls
- Always synchronized with game

**Implementation**:
```python
def extract_weather_from_game(game: dict) -> dict:
    """Extract weather data from ESPN game event"""
    weather = game.get('weather', {})
    return {
        'temperature': weather.get('temperature'),
        'condition': weather.get('displayValue'),
        'wind_speed': weather.get('windSpeed'),
        'indoor': game.get('competitions', [{}])[0].get('venue', {}).get('indoor', False)
    }
```

**File to modify**: [src/utils/weather.py](src/utils/weather.py)

---

### Priority 2: Consolidated Score Updates ⭐⭐⭐
**Current**: Multiple sources for scores  
**Improvement**: Use ESPN as primary, others as fallback

**Benefits**:
- Simpler pipeline
- More reliable
- Faster updates

**Implementation**:
```python
def update_game_scores(date: str):
    """Update scores from ESPN API"""
    url = f"{ESPN_BASE}/scoreboard?dates={date.replace('-', '')}"
    resp = requests.get(url).json()
    
    for event in resp.get('events', []):
        comp = event['competitions'][0]
        competitors = comp['competitors']
        
        # Only update if game is final
        if comp['status']['type']['state'] == 'post':
            away = next(t for t in competitors if t['homeAway'] == 'away')
            home = next(t for t in competitors if t['homeAway'] == 'home')
            
            # Update database
            update_db(
                game_id=event['id'],
                away_score=int(away['score']),
                home_score=int(home['score'])
            )
```

**File to create/modify**: [src/scripts/update_postgame_scores.py](src/scripts/update_postgame_scores.py)

---

### Priority 3: Historical Backfill ⭐⭐
**Current**: Manual data imports from multiple sources  
**Improvement**: Automate historical game fetching

**Benefits**:
- Fill gaps in historical data
- Consistent data format
- Automated updates

**Implementation**:
```python
def backfill_games(start_date: str, end_date: str):
    """Backfill games from ESPN API"""
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    while current <= end:
        date_str = current.strftime('%Y%m%d')
        url = f"{ESPN_BASE}/scoreboard?dates={date_str}"
        
        # Fetch and store games
        resp = requests.get(url).json()
        games = parse_espn_games(resp)
        save_to_db(games)
        
        current += timedelta(days=1)
        time.sleep(0.5)  # Rate limiting
```

**File to create**: [src/scripts/backfill_espn_games.py](src/scripts/backfill_espn_games.py)

---

### Priority 4: Team Standardization ⭐
**Current**: Manual team code mapping  
**Improvement**: Dynamic team lookup from API

**Benefits**:
- Handles team relocations
- Automatic updates
- Consistent abbreviations

**Implementation**:
```python
def get_team_mapping():
    """Get official team abbreviations from ESPN"""
    url = f"{ESPN_BASE}/teams"
    resp = requests.get(url).json()
    
    teams = {}
    for sport in resp.get('sports', []):
        for league in sport.get('leagues', []):
            for team_obj in league.get('teams', []):
                team = team_obj['team']
                teams[team['abbreviation']] = {
                    'id': team['id'],
                    'name': team['displayName'],
                    'location': team['location']
                }
    return teams
```

**File to create**: [src/utils/team_mapping.py](src/utils/team_mapping.py)

---

## Data Quality Comparison

| Feature | ESPN API | PFR Scraping | Current Status |
|---------|----------|--------------|----------------|
| **Live Scores** | ✅ Real-time | ❌ Delayed | ESPN used |
| **Game Schedule** | ✅ Structured | ⚠️ Manual | ESPN used |
| **Weather** | ✅ Included | ⚠️ External | ⚠️ Not using ESPN |
| **Historical Games** | ✅ Available | ✅ Comprehensive | PFR used |
| **Team Stats** | ⚠️ Basic | ✅ Detailed | PFR used |
| **Advanced Stats** | ⚠️ Limited | ✅ Extensive | PFR used |
| **Reliability** | ✅ High | ⚠️ Scraping risk | Mixed |
| **Speed** | ✅ Fast API | ⚠️ Slower scraping | Mixed |

**Recommendation**: Use ESPN for real-time/schedule data, PFR for historical advanced stats

---

## Integration Architecture

### Proposed Data Flow

```
ESPN API (Primary - Real-time)
    ↓
    ├─→ Upcoming Games (already implemented)
    ├─→ Live Scores (new)
    ├─→ Weather Data (new - replace external)
    └─→ Schedule/Dates (already implemented)

PFR Scraping (Secondary - Historical depth)
    ↓
    ├─→ Advanced Team Stats (existing)
    ├─→ Player Stats (existing)
    └─→ Historical Backfill (existing)

Database (SQLite)
    ↓
    └─→ Unified storage for all sources
```

### Data Source Priority

1. **Real-time game data** → ESPN API (fast, reliable)
2. **Weather** → ESPN API (synchronized with games)
3. **Advanced stats** → PFR (comprehensive, detailed)
4. **Historical backfill** → ESPN + PFR (combination)

---

## Implementation Roadmap

### Phase 1: Fix API Service (Immediate)
**Time**: 1-2 hours  
**Impact**: HIGH

- [x] Identify API startup issue (port conflict)
- [ ] Fix port binding
- [ ] Add proper error handling
- [ ] Document ESPN endpoints in API

**Files**:
- [src/nfl_model/services/api/app.py](src/nfl_model/services/api/app.py)

---

### Phase 2: Weather Integration (High Priority)
**Time**: 1 day  
**Impact**: MEDIUM-HIGH

- [ ] Extract weather from ESPN game events
- [ ] Update weather.py to use ESPN data
- [ ] Backfill weather for recent games
- [ ] Update feature builder to use new weather source

**Files**:
- [src/utils/weather.py](src/utils/weather.py)
- [src/utils/upcoming_games.py](src/utils/upcoming_games.py)
- [src/utils/feature_builder.py](src/utils/feature_builder.py)

---

### Phase 3: Consolidated Score Updates (High Priority)
**Time**: 1 day  
**Impact**: MEDIUM

- [ ] Create ESPN score updater
- [ ] Use ESPN as primary score source
- [ ] Keep PFR as fallback
- [ ] Automate daily score updates

**Files**:
- [src/scripts/update_postgame_scores.py](src/scripts/update_postgame_scores.py)
- [src/scripts/pipeline_daily_sync.py](src/scripts/pipeline_daily_sync.py)

---

### Phase 4: Historical Backfill (Medium Priority)
**Time**: 2 days  
**Impact**: MEDIUM

- [ ] Create backfill script for ESPN
- [ ] Fill gaps in 2025 data (5 missing games)
- [ ] Validate against existing data
- [ ] Document backfill process

**Files**:
- [src/scripts/backfill_espn_games.py](src/scripts/backfill_espn_games.py) (new)

---

### Phase 5: API Enhancements (Low Priority)
**Time**: 2 days  
**Impact**: LOW-MEDIUM

- [ ] Add ESPN proxy endpoints to FastAPI
- [ ] Expose team data via API
- [ ] Add standing data
- [ ] Create API documentation

**Files**:
- [src/nfl_model/services/api/app.py](src/nfl_model/services/api/app.py)
- [docs/architecture/API_GUIDE.md](docs/architecture/API_GUIDE.md) (new)

---

## ESPN API Limitations

### What ESPN API Does NOT Provide

1. **Advanced Team Statistics** ❌
   - No detailed offensive/defensive stats
   - No player-level performance
   - → Keep using PFR for this

2. **Historical Depth** ⚠️
   - Good for recent seasons
   - May not have full 2020-2025 historical stats
   - → Use PFR for comprehensive historical data

3. **Detailed Play-by-Play** ❌
   - No drive data
   - No play-by-play stats
   - → Not needed for your model

4. **Injury Reports** ❌
   - No injury data
   - → Would need separate source if needed

5. **Betting Lines** ⚠️
   - Inconsistent odds data
   - Not always available
   - → Keep existing odds sources

---

## Code Examples

### Example 1: Fetch Current Week Games
```python
import requests

url = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
resp = requests.get(url).json()

for event in resp['events']:
    comp = event['competitions'][0]
    away = next(t for t in comp['competitors'] if t['homeAway'] == 'away')
    home = next(t for t in comp['competitors'] if t['homeAway'] == 'home')
    
    print(f"{away['team']['abbreviation']} @ {home['team']['abbreviation']}")
    print(f"Score: {away.get('score', 'TBD')} - {home.get('score', 'TBD')}")
    print(f"Status: {comp['status']['type']['name']}")
```

### Example 2: Fetch Games for Specific Date
```python
date = "20260111"
url = f"http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={date}"
resp = requests.get(url).json()

games = []
for event in resp['events']:
    games.append({
        'id': event['id'],
        'date': event['date'],
        'teams': [t['team']['abbreviation'] for t in event['competitions'][0]['competitors']]
    })
```

### Example 3: Extract Weather
```python
def get_game_weather(game_event):
    weather = game_event.get('weather', {})
    venue = game_event['competitions'][0].get('venue', {})
    
    return {
        'temperature': weather.get('temperature'),
        'condition': weather.get('displayValue'),
        'indoor': venue.get('indoor', False),
        'wind_speed': weather.get('windSpeed')
    }
```

---

## Recommendation Summary

### ✅ DO

1. **Expand ESPN API usage** - It's already integrated, just use more of it
2. **Use ESPN for real-time data** - Scores, schedules, weather
3. **Keep PFR for advanced stats** - Team/player detailed performance
4. **Fix API service first** - Unblock development
5. **Extract weather from ESPN** - Eliminate external weather scraping

### ❌ DON'T

1. **Replace PFR completely** - It provides valuable advanced stats
2. **Rely on ESPN for historical stats** - PFR is better for this
3. **Use ESPN for odds** - Unreliable, keep existing sources
4. **Over-complicate** - ESPN API is simple, keep it that way

---

## Cost-Benefit Analysis

| Integration Task | Effort | Impact | Priority | ROI |
|------------------|--------|--------|----------|-----|
| Fix API Service | 2 hours | HIGH | 1 | ⭐⭐⭐⭐⭐ |
| Weather from ESPN | 1 day | MEDIUM | 2 | ⭐⭐⭐⭐ |
| Score consolidation | 1 day | MEDIUM | 3 | ⭐⭐⭐⭐ |
| Historical backfill | 2 days | MEDIUM | 4 | ⭐⭐⭐ |
| API enhancements | 2 days | LOW | 5 | ⭐⭐ |
| **TOTAL** | **6 days** | **HIGH** | - | **⭐⭐⭐⭐** |

---

## Conclusion

**ESPN API is an excellent fit for your NFL Model project.**

**Strengths**:
- ✅ Already partially integrated
- ✅ Comprehensive real-time data
- ✅ Free and reliable
- ✅ Well-structured JSON
- ✅ Includes weather data

**Recommended Action Plan**:
1. **Week 1**: Fix API service + extract weather from ESPN
2. **Week 2**: Consolidate score updates to use ESPN
3. **Week 3**: Backfill missing 2025 games
4. **Week 4**: Enhance API with ESPN proxy endpoints

**Expected Outcome**: Simplified data pipeline, more reliable real-time data, reduced scraping overhead.

---

**Next Steps**: Proceed with fixing API service, then implement weather extraction from ESPN events.

**Document Status**: ✅ Ready for Implementation  
**Last Updated**: 2026-01-11
