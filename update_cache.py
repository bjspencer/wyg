#!/usr/bin/env python3
"""
Script to update the NBA players cache file.
Can be run standalone or via GitHub Actions.
"""
import os
import sys
import time
import socket
import requests
import urllib3
import pandas as pd
from datetime import datetime
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Set global socket timeout for all connections
socket.setdefaulttimeout(120)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure requests session with retries and longer timeout
def _create_session_with_retries(timeout=120):
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Disable SSL verification
    session.verify = False
    return session

# Create a global session with retries
_global_session = _create_session_with_retries(timeout=120)

# Import nba_api after setting up session
from nba_api.stats.endpoints import (
    leaguedashplayerstats,
    playerindex,
    playerawards,
    commonplayerinfo,
)

# Monkey patch requests to use our session with proper timeout
_original_send = requests.Session.send

def _send_with_timeout(self, *args, **kwargs):
    kwargs['timeout'] = kwargs.get('timeout', 120)
    kwargs['verify'] = False
    return _original_send(self, *args, **kwargs)

requests.Session.send = _send_with_timeout

CACHE_FILE = "nba_players_cache.csv"
SEASON = "2025-26"

TEAM_CONFERENCE = {
    'ATL': 'East', 'BOS': 'East', 'BKN': 'East', 'CHA': 'East', 'CHI': 'East',
    'CLE': 'East', 'DAL': 'West', 'DEN': 'West', 'DET': 'East', 'GSW': 'West',
    'HOU': 'West', 'IND': 'East', 'LAC': 'West', 'LAL': 'West', 'MEM': 'West',
    'MIA': 'East', 'MIL': 'East', 'MIN': 'West', 'NOP': 'West', 'NYK': 'East',
    'OKC': 'West', 'ORL': 'East', 'PHI': 'East', 'PHX': 'West', 'POR': 'West',
    'SAC': 'West', 'SAS': 'West', 'TOR': 'East', 'UTA': 'West', 'WAS': 'East',
}

TEAM_DIVISION = {
    'ATL': 'Southeast', 'MIA': 'Southeast', 'CHA': 'Southeast', 'ORL': 'Southeast', 'WAS': 'Southeast',
    'BOS': 'Atlantic', 'BKN': 'Atlantic', 'NYK': 'Atlantic', 'PHI': 'Atlantic', 'TOR': 'Atlantic',
    'CHI': 'Central', 'CLE': 'Central', 'DET': 'Central', 'IND': 'Central', 'MIL': 'Central',
    'DAL': 'Southwest', 'HOU': 'Southwest', 'MEM': 'Southwest', 'NOP': 'Southwest', 'SAS': 'Southwest',
    'DEN': 'Northwest', 'MIN': 'Northwest', 'OKC': 'Northwest', 'POR': 'Northwest', 'UTA': 'Northwest',
    'GSW': 'Pacific', 'LAC': 'Pacific', 'LAL': 'Pacific', 'PHX': 'Pacific', 'SAC': 'Pacific',
}

EUROPE = {'France', 'Germany', 'Spain', 'Serbia', 'Slovenia', 'Croatia', 'Italy', 'Greece',
          'Latvia', 'Lithuania', 'Czech Republic', 'Bosnia', 'Montenegro', 'Turkey', 'Belgium',
          'Finland', 'Georgia', 'Poland', 'Ukraine', 'Sweden', 'Estonia', 'Hungary', 'Kosovo',
          'North Macedonia', 'Portugal', 'Romania', 'Russia', 'Switzerland', 'Netherlands', 'Denmark'}
AFRICA = {'Democratic Republic of the Congo', 'Nigeria', 'Cameroon', 'Senegal', 'South Sudan',
          'Sudan', 'Somalia', 'Republic of the Congo', 'Angola', 'Ghana', 'Mali', 'Guinea',
          'Ivory Coast', 'Morocco', 'Central African Republic'}
SOUTH_AMERICA = {'Brazil', 'Argentina', 'Venezuela', 'Colombia', 'Chile', 'Uruguay', 'Bolivia'}
PLAYOFF_TEAMS = {'DET', 'BOS', 'NYK', 'CLE', 'TOR', 'ATL', 'PHI', 'OKC', 'SAS', 'DEN', 'LAL', 'HOU', 'MIN', 'POR'}

NBA_BROTHERS = {
    'Lonzo Ball': 'LaMelo Ball',
    'Max Christie': 'Cam Christie',
    'Stephen Curry': 'Seth Curry',
    'Jrue Holiday': 'Justin Holiday',
    'Tyus Jones': 'Tre Jones',
    'Brook Lopez': 'Robin Lopez',
    'Caleb Martin': 'Cody Martin',
    'Evan Mobley': 'Isaiah Mobley',
    'Marcus Morris': 'Markieff Morris',
    'Amen Thompson': 'Ausar Thompson',
    'Franz Wagner': 'Moritz Wagner',
    'Cason Wallace': 'Keaton Wallace',
    'Julian Champagnie': 'Justin Champagnie',
    'Obi Toppin': 'Jacob Toppin',
    'Pat Spencer': 'Cam Spencer',
    'Emanuel Miller': 'Leonard Miller',
    'Marvin Bagley III': 'Marcus Bagley',
    'Giannis Antetokoumnpo': 'Thanasis Antetokoumnpo',
}


def fetch_with_retries(fetch_func, max_retries=5, initial_delay=3):
    """Retry a fetch operation with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return fetch_func()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, 
                requests.exceptions.ReadTimeout,
                urllib3.exceptions.ReadTimeoutError,
                urllib3.exceptions.PoolError,
                urllib3.exceptions.ConnectTimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            print(f"  Request timed out (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...")
            time.sleep(delay)


def fetch_and_update_cache():
    """Fetch player data from NBA API and update the cache file."""
    print(f"[{datetime.now().isoformat()}] Starting cache update...")

    try:
        print("Fetching league dash player stats...")
        totals_df = fetch_with_retries(
            lambda: leaguedashplayerstats.LeagueDashPlayerStats(
                season=SEASON, season_type_all_star='Regular Season'
            ).get_data_frames()[0]
        )

        print("Fetching player index...")
        bio_df = fetch_with_retries(
            lambda: playerindex.PlayerIndex(season=SEASON).get_data_frames()[0]
        )
        bio_df = bio_df.rename(columns={'PERSON_ID': 'PLAYER_ID'})
        bio_df['PLAYER_ID'] = bio_df['PLAYER_ID'].astype(int)
        bio_lookup = bio_df.set_index('PLAYER_ID')

        print("Processing player data...")
        rows = []
        total_players = len(totals_df)

        for idx, row in totals_df.iterrows():
            if (idx + 1) % 50 == 0:
                print(f"  Processing player {idx + 1}/{total_players}...")

            gp = row['GP'] if row['GP'] > 0 else 1
            ppg = row['PTS'] / gp
            rpg = row['REB'] / gp
            apg = row['AST'] / gp
            team = row.get('TEAM_ABBREVIATION', '')
            conference = TEAM_CONFERENCE.get(team, '')
            division = TEAM_DIVISION.get(team, '')
            pid = int(row['PLAYER_ID'])

            bio = bio_lookup.loc[pid] if pid in bio_lookup.index else {}

            player_info = commonplayerinfo.CommonPlayerInfo(player_id=pid).get_data_frames()[0]

            def safe(key):
                v = bio.get(key, '') if isinstance(bio, dict) else (bio[key] if key in bio.index else '')
                return '' if pd.isna(v) else str(v).strip()

            school = safe('COLLEGE')
            country = safe('COUNTRY')
            jersey = safe('JERSEY_NUMBER')

            try:
                jersey_num = int(jersey)
            except (ValueError, TypeError):
                jersey_num = -1

            try:
                age = int(float(row.get('AGE', 0) or 0))
            except (ValueError, TypeError):
                age = 0

            height_str = safe('HEIGHT')
            try:
                h_parts = height_str.split('-')
                height_inches = int(h_parts[0]) * 12 + int(h_parts[1])
            except (ValueError, IndexError):
                height_inches = 0

            draft_round = safe('DRAFT_ROUND')
            try:
                draft_num = int(safe('DRAFT_NUMBER'))
            except (ValueError, TypeError):
                draft_num = -1

            try:
                draft_year = int(safe('DRAFT_YEAR'))
            except (ValueError, TypeError):
                draft_year = 0

            is_first_round = int(draft_round == '1')
            is_lottery = int(draft_round == '1' and 1 <= draft_num <= 14)
            is_undrafted = int(not draft_round or draft_round.lower() == 'undrafted')
            seasons_played = max(0, 2026 - draft_year + 1) if draft_year > 0 else 0

            try:
                aw = fetch_with_retries(
                    lambda pid=pid: playerawards.PlayerAwards(player_id=pid).get_data_frames()[0]
                )
                descs = set(aw['DESCRIPTION'].tolist())
                all_star_count = int((aw['DESCRIPTION'] == 'All-Star').sum())
            except Exception as e:
                descs = set()
                all_star_count = 0
                # Don't break on individual player award fetch - just skip
                # print(f"  Warning: Could not fetch awards for player {pid}: {e}")
                time.sleep(1)  # Delay after failed player award fetch

            has_ring = int('NBA Champion' in descs)
            has_allnba = int('All-NBA' in descs)
            has_all_defense = int('All-Defensive Team' in descs)
            is_mvp = int('Most Valuable Player' in descs)
            is_dpoy = int('Defensive Player of the Year' in descs)
            is_allstar = int(all_star_count > 0)
            is_3x_allstar = int(all_star_count >= 3)

            mpg = round(row['MIN'] / gp, 2) if gp > 0 else 0
            spg = row.get('STL', 0) / gp if gp > 0 else 0
            bpg = row.get('BLK', 0) / gp if gp > 0 else 0
            fg3pm = row.get('FG3M', 0) / gp if gp > 0 else 0
            oreb = row.get('OREB', 0) / gp if gp > 0 else 0
            tov = row.get('TOV', 0) / gp if gp > 0 else 0
            player_name = row['PLAYER_NAME']
            last_name = player_name.split()[-1]
            first_name = player_name.split()[0]

            rows.append({
                'Player': player_name,
                'PLAYER_ID': pid,
                'Averages 25+ PPG this season?': int(ppg >= 25),
                'Averages 20+ PPG this season?': int(ppg >= 20),
                'Averages 15+ PPG this season?': int(ppg >= 15),
                'Averages 10+ PPG this season?': int(ppg >= 10),
                'Averages 10+ RPG this season?': int(rpg >= 10),
                'Averages 5+ RPG this season?': int(rpg >= 5),
                'Averages 7+ APG this season?': int(apg >= 7),
                'Averages 4+ APG this season?': int(apg >= 4),
                'Averages 1.5+ SPG this season?': int(spg >= 1.5),
                'Averages 1+ SPG this season?': int(spg >= 1),
                'Averages 1.5+ BPG this season?': int(bpg >= 1.5),
                'Averages 1+ BPG this season?': int(bpg >= 1),
                'Averages 3+ 3PM this season?': int(fg3pm >= 3),
                'Averages 1+ 3PM this season?': int(fg3pm >= 1),
                'Averages 30+ min per game this season?': int(mpg >= 30),
                'Averages 20+ min per game this season?': int(mpg >= 20),
                'Shoots 50%+ from the field this season?': int(row.get('FG_PCT', 0) >= 0.50),
                'Shoots 35%+ from three this season?': int(row.get('FG3_PCT', 0) >= 0.35),
                'Shoots 80%+ from the line this season?': int(row.get('FT_PCT', 0) >= 0.80),
                'Averages 3+ offensive rebounds this season?': int(oreb >= 3),
                'Averages 3+ turnovers this season?': int(tov >= 3),
                'Played 50+ games this season?': int(row['GP'] >= 50),
                'Played 70+ games this season?': int(row['GP'] >= 70),
                'Plays in the Eastern Conference?': int(conference == 'East'),
                'Plays in the Western Conference?': int(conference == 'West'),
                'Plays in the Atlantic Division?': int(division == 'Atlantic'),
                'Plays in the Central Division?': int(division == 'Central'),
                'Plays in the Southeast Division?': int(division == 'Southeast'),
                'Plays in the Northwest Division?': int(division == 'Northwest'),
                'Plays in the Pacific Division?': int(division == 'Pacific'),
                'Plays in the Southwest Division?': int(division == 'Southwest'),
                'Is his jersey number less than 10?': int(0 <= jersey_num < 10),
                'Is his jersey number between 10 and 19?': int(10 <= jersey_num <= 19),
                'Is his jersey number between 20 and 29?': int(20 <= jersey_num <= 29),
                'Is his jersey number 30 or higher?': int(jersey_num >= 30),
                'Is his jersey number an odd number?': int(jersey_num >= 0 and jersey_num % 2 == 1),
                'Is he from the United States?': int(country in ('USA', 'United States')),
                'Is he from Europe?': int(country in EUROPE),
                'Is he from Africa?': int(country in AFRICA),
                'Is he from Canada?': int(country == 'Canada'),
                'Is he from Australia?': int(country in ('Australia', 'New Zealand')),
                'Is he from South America?': int(country in SOUTH_AMERICA),
                'Did he play college basketball?': int(bool(school) and school.upper() not in ('', 'NONE', 'N/A')),
                'MPG': mpg,
                'Is he 25 or younger?': int(0 < age <= 25),
                'Is he 30 or older?': int(age >= 30),
                'Is he 6-8 or taller?': int(height_inches >= 80),
                'Is he 7 feet or taller?': int(height_inches >= 84),
                'Was he a first-round pick?': is_first_round,
                'Was he a lottery pick (top 14)?': is_lottery,
                'Was he undrafted?': is_undrafted,
                'Averages 5+ APG?': int(apg >= 5),
                'Averages 8+ RPG?': int(rpg >= 8),
                'Shoots 40%+ from three?': int(row.get('FG3_PCT', 0) >= 0.40),
                'Does his last name start with A-M?': int(last_name[0].upper() <= 'M') if last_name else 0,
                'Does his first name start with A-M?': int(first_name[0].upper() <= 'M') if first_name else 0,
                'Does his last name have more than 6 letters?': int(len(last_name) > 6) if last_name else 0,
                'Does his first name end in a vowel?': int(first_name[-1].upper() in 'AEIOU') if first_name else 0,
                'Has he been an All-Star?': is_allstar,
                'Has he been an All-Star 3+ times?': is_3x_allstar,
                'Has he won an NBA Championship?': has_ring,
                'Has he been All-NBA?': has_allnba,
                'Has he won the MVP award?': is_mvp,
                'Has he won Defensive Player of the Year?': is_dpoy,
                'Has he made an All-Defensive Team?': has_all_defense,
                'Does he play for a 2026 playoff team?': int(team in PLAYOFF_TEAMS),
                'Has he scored 10,000+ career points?': int(row.get('PTS', 0) >= 10000),
                'Has he grabbed 5,000+ career rebounds?': int(row.get('REB', 0) >= 5000),
                'Has he dished 5,000+ career assists?': int(row.get('AST', 0) >= 5000),
                'Has he played for 3+ teams in his career?': int(len(set(team.split('-'))) >= 3) if '-' in team else 0,
                'Has he played for 10+ seasons?': int(seasons_played >= 10),
                'Was he traded this season?': int(len(set(team.split('-'))) > 1) if '-' in team else 0,
                'Does he have a brother in the NBA?': int(player_name in NBA_BROTHERS or player_name in NBA_BROTHERS.values()),
            })
            
            # Delay between players to avoid overwhelming the API and reduce timeout risk
            time.sleep(0.2)

        print(f"Creating DataFrame with {len(rows)} players...")
        df = pd.DataFrame(rows)

        print(f"Saving cache to {CACHE_FILE}...")
        df.to_csv(CACHE_FILE, index=False)

        print(f"✓ Cache updated successfully at {datetime.now().isoformat()}")
        print(f"  Total players: {len(df)}")
        return True

    except Exception as e:
        print(f"✗ Error updating cache: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = fetch_and_update_cache()
    sys.exit(0 if success else 1)
