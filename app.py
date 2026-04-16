import sys
import random
import os
import time
import requests
import urllib3
import pandas as pd
import streamlit as st
 
sys.stdout.reconfigure(encoding='utf-8')
 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_original_send = requests.Session.send
def _send_no_verify(self, *args, **kwargs):
    kwargs['verify'] = False
    return _original_send(self, *args, **kwargs)
requests.Session.send = _send_no_verify
 
from nba_api.stats.endpoints import leaguedashplayerstats, playerindex, playerawards
 
CACHE_FILE = "nba_players_cache.csv"
CACHE_MAX_DAYS = 7
SEASON = "2025-26"
 
TEAM_CONFERENCE = {
    'ATL': 'East', 'BOS': 'East', 'BKN': 'East', 'CHA': 'East', 'CHI': 'East',
    'CLE': 'East', 'DAL': 'West', 'DEN': 'West', 'DET': 'East', 'GSW': 'West',
    'HOU': 'West', 'IND': 'East', 'LAC': 'West', 'LAL': 'West', 'MEM': 'West',
    'MIA': 'East', 'MIL': 'East', 'MIN': 'West', 'NOP': 'West', 'NYK': 'East',
    'OKC': 'West', 'ORL': 'East', 'PHI': 'East', 'PHX': 'West', 'POR': 'West',
    'SAC': 'West', 'SAS': 'West', 'TOR': 'East', 'UTA': 'West', 'WAS': 'East',
}
COLLEGE_CONFERENCE_TEAMS={
    'ACC': {'Duke', 'North Carolina', 'Virginia', 'Florida State', 'Louisville'},
    'Big 12': {'Kansas', 'Baylor', 'Texas Tech', 'Oklahoma State', 'West Virginia'},
    'Big Ten': {'Michigan', 'Michigan State', 'Ohio State', 'Illinois', 'Wisconsin'},
    'Pac-12': {'UCLA', 'Arizona', 'USC', 'Oregon', 'Colorado'},
    'SEC': {'Kentucky', 'Florida', 'Tennessee', 'Auburn', 'Alabama'},
    'AAC': {'Houston', 'Memphis', 'Cincinnati', 'SMU', 'UCF'},
    'Mountain West': {'San Diego State', 'Boise State', 'Fresno State', 'Nevada', 'Colorado State'},
    'Sun Belt': {'Appalachian State', 'Arkansas State', 'Coastal Carolina', 'Georgia State', 'Louisiana'},
    'Conference USA': {'Western Kentucky', 'Old Dominion', 'Charlotte', 'Florida Atlantic', 'UTEP'},
    'MAC': {'Buffalo', 'Toledo', 'Ohio', 'Akron', 'Ball State'},
    'Big Sky': {'Montana', 'Eastern Washington', 'Weber State', 'Northern Arizona', 'Idaho State'},
    'Big South': {'Winthrop', 'Radford', 'UNC Asheville', 'Campbell', 'Gardner-Webb'},
    'Big West': {'UC Santa Barbara', 'UC Irvine', 'Long Beach State', 'Cal State Fullerton', 'Hawaii'},
    'Colonial': {'VCU', 'Hofstra', 'UNC Wilmington', 'Elon', 'Drexel'},
    'Horizon': {'Wright State', 'Oakland', 'Green Bay', 'Northern Kentucky', 'IUPUI'},
    'Ivy League': {'Yale', 'Harvard', 'Princeton', 'Penn', 'Columbia'},
    'MAAC': {'Iona', 'Monmouth', 'Siena', 'Marist', 'Canisius'},
    'MEAC': {'Norfolk State', 'North Carolina A&T', 'Bethune-Cookman', 'Florida A&M', 'Howard'},
    'Missouri Valley': {'Loyola Chicago', 'Bradley', 'Valparaiso', 'Southern Illinois', 'Indiana State'},
    'Northeast': {'Fairleigh Dickinson', 'Mount St. Mary\'s', 'St. Francis Brooklyn', 'Bryant', 'Central Connecticut'},
    'Ohio Valley': {'Murray State', 'Austin Peay', 'Eastern Kentucky', 'Tennessee State', 'Southeast Missouri State'},
    'Patriot League': {'Colgate', 'Bucknell', 'Lehigh', 'Lafayette', 'American'},
    'Southern': {'Wofford', 'Furman', 'Samford', 'Mercer', 'Chattanooga'},
    'Southland': {'Stephen F. Austin', 'Lamar', 'Central Arkansas', 'Abilene Christian', 'Incarnate Word'},
    'SWAC': {'Alabama State', 'Alcorn State', 'Grambling State', 'Jackson State', 'Prairie View A&M'},
    'Summit League': {'South Dakota State', 'North Dakota State', 'Oral Roberts', 'Denver', 'Western Illinois'},
    'WAC': {'Grand Canyon', 'Seattle', 'New Mexico State', 'UT Rio Grande Valley', 'California Baptist'},
    'Big East': {'Villanova', 'Providence', 'Seton Hall', 'Marquette', 'Georgetown'},
    'ASUN': {'Liberty', 'Florida Gulf Coast', 'North Florida', 'Stetson', 'Lipscomb'},
    'West Coast': {'Gonzaga', 'Saint Mary\'s', 'BYU', 'San Francisco', 'Santa Clara'},
    'Atlantic 10': {'Dayton', 'VCU', 'Saint Louis', 'Richmond', 'Davidson'},
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
 
IMPLICATIONS = {
    ('Plays in the Eastern Conference?', 1): [('Plays in the Western Conference?', 0), ('Plays in the Northwest Division?', 0), ('Plays in the Pacific Division?', 0), ('Plays in the Southwest Division?', 0)],
    ('Plays in the Eastern Conference?', 0): [('Plays in the Western Conference?', 1), ('Plays in the Atlantic Division?', 0), ('Plays in the Central Division?', 0), ('Plays in the Southeast Division?', 0)],
    ('Plays in the Western Conference?', 1): [('Plays in the Eastern Conference?', 0), ('Plays in the Atlantic Division?', 0), ('Plays in the Central Division?', 0), ('Plays in the Southeast Division?', 0)],
    ('Plays in the Western Conference?', 0): [('Plays in the Eastern Conference?', 1), ('Plays in the Northwest Division?', 0), ('Plays in the Pacific Division?', 0), ('Plays in the Southwest Division?', 0)],
    ('Plays in the Atlantic Division?', 1):   [('Plays in the Eastern Conference?', 1), ('Plays in the Western Conference?', 0), ('Plays in the Central Division?', 0), ('Plays in the Southeast Division?', 0), ('Plays in the Northwest Division?', 0), ('Plays in the Pacific Division?', 0), ('Plays in the Southwest Division?', 0)],
    ('Plays in the Central Division?', 1):    [('Plays in the Eastern Conference?', 1), ('Plays in the Western Conference?', 0), ('Plays in the Atlantic Division?', 0), ('Plays in the Southeast Division?', 0), ('Plays in the Northwest Division?', 0), ('Plays in the Pacific Division?', 0), ('Plays in the Southwest Division?', 0)],
    ('Plays in the Southeast Division?', 1):  [('Plays in the Eastern Conference?', 1), ('Plays in the Western Conference?', 0), ('Plays in the Atlantic Division?', 0), ('Plays in the Central Division?', 0), ('Plays in the Northwest Division?', 0), ('Plays in the Pacific Division?', 0), ('Plays in the Southwest Division?', 0)],
    ('Plays in the Northwest Division?', 1):  [('Plays in the Western Conference?', 1), ('Plays in the Eastern Conference?', 0), ('Plays in the Atlantic Division?', 0), ('Plays in the Central Division?', 0), ('Plays in the Southeast Division?', 0), ('Plays in the Pacific Division?', 0), ('Plays in the Southwest Division?', 0)],
    ('Plays in the Pacific Division?', 1):    [('Plays in the Western Conference?', 1), ('Plays in the Eastern Conference?', 0), ('Plays in the Atlantic Division?', 0), ('Plays in the Central Division?', 0), ('Plays in the Southeast Division?', 0), ('Plays in the Northwest Division?', 0), ('Plays in the Southwest Division?', 0)],
    ('Plays in the Southwest Division?', 1):  [('Plays in the Western Conference?', 1), ('Plays in the Eastern Conference?', 0), ('Plays in the Atlantic Division?', 0), ('Plays in the Central Division?', 0), ('Plays in the Southeast Division?', 0), ('Plays in the Northwest Division?', 0), ('Plays in the Pacific Division?', 0)],
    ('Averages 25+ PPG this season?', 1): [('Averages 20+ PPG this season?', 1), ('Averages 15+ PPG this season?', 1), ('Averages 10+ PPG this season?', 1)],
    ('Averages 20+ PPG this season?', 1): [('Averages 15+ PPG this season?', 1), ('Averages 10+ PPG this season?', 1)],
    ('Averages 15+ PPG this season?', 1): [('Averages 10+ PPG this season?', 1)],
    ('Averages 10+ PPG this season?', 0): [('Averages 15+ PPG this season?', 0), ('Averages 20+ PPG this season?', 0), ('Averages 25+ PPG this season?', 0)],
    ('Averages 15+ PPG this season?', 0): [('Averages 20+ PPG this season?', 0), ('Averages 25+ PPG this season?', 0)],
    ('Averages 20+ PPG this season?', 0): [('Averages 25+ PPG this season?', 0)],
    ('Averages 10+ RPG this season?', 1): [('Averages 8+ RPG?', 1), ('Averages 5+ RPG this season?', 1)],
    ('Averages 8+ RPG?', 1):  [('Averages 5+ RPG this season?', 1)],
    ('Averages 5+ RPG this season?', 0):  [('Averages 8+ RPG?', 0), ('Averages 10+ RPG this season?', 0)],
    ('Averages 8+ RPG?', 0):  [('Averages 10+ RPG this season?', 0)],
    ('Averages 7+ APG this season?', 1):  [('Averages 5+ APG?', 1), ('Averages 4+ APG this season?', 1)],
    ('Averages 5+ APG?', 1):  [('Averages 4+ APG this season?', 1)],
    ('Averages 4+ APG this season?', 0):  [('Averages 5+ APG?', 0), ('Averages 7+ APG this season?', 0)],
    ('Averages 5+ APG?', 0):  [('Averages 7+ APG this season?', 0)],
    ('Averages 1.5+ SPG this season?', 1): [('Averages 1+ SPG this season?', 1)],
    ('Averages 1+ SPG this season?', 0):   [('Averages 1.5+ SPG this season?', 0)],
    ('Averages 1.5+ BPG this season?', 1): [('Averages 1+ BPG this season?', 1)],
    ('Averages 1+ BPG this season?', 0):   [('Averages 1.5+ BPG this season?', 0)],
    ('Averages 3+ 3PM this season?', 1):  [('Averages 1+ 3PM this season?', 1)],
    ('Averages 1+ 3PM this season?', 0):  [('Averages 3+ 3PM this season?', 0)],
    ('Averages 30+ min per game this season?', 1): [('Averages 20+ min per game this season?', 1)],
    ('Averages 20+ min per game this season?', 0): [('Averages 30+ min per game this season?', 0)],
    ('Played 70+ games this season?', 1): [('Played 50+ games this season?', 1)],
    ('Played 50+ games this season?', 0): [('Played 70+ games this season?', 0)],
    ('Is his jersey number less than 10?', 1):        [('Is his jersey number between 10 and 19?', 0), ('Is his jersey number between 20 and 29?', 0), ('Is his jersey number 30 or higher?', 0)],
    ('Is his jersey number between 10 and 19?', 1):   [('Is his jersey number less than 10?', 0), ('Is his jersey number between 20 and 29?', 0), ('Is his jersey number 30 or higher?', 0)],
    ('Is his jersey number between 20 and 29?', 1):   [('Is his jersey number less than 10?', 0), ('Is his jersey number between 10 and 19?', 0), ('Is his jersey number 30 or higher?', 0)],
    ('Is his jersey number 30 or higher?', 1):        [('Is his jersey number less than 10?', 0), ('Is his jersey number between 10 and 19?', 0), ('Is his jersey number between 20 and 29?', 0)],
    ('Is he a guard?', 1):   [('Is he a forward?', 0), ('Is he a center?', 0)],
    ('Is he a forward?', 1): [('Is he a guard?', 0), ('Is he a center?', 0)],
    ('Is he a center?', 1):  [('Is he a guard?', 0), ('Is he a forward?', 0)],
    ('Is he from the United States?', 1): [('Is he from Europe?', 0), ('Is he from Africa?', 0), ('Is he from Canada?', 0), ('Is he from Australia?', 0), ('Is he from South America?', 0)],
    ('Is he from Europe?', 1):            [('Is he from the United States?', 0), ('Is he from Africa?', 0), ('Is he from Canada?', 0), ('Is he from Australia?', 0), ('Is he from South America?', 0)],
    ('Is he from Africa?', 1):            [('Is he from the United States?', 0), ('Is he from Europe?', 0), ('Is he from Canada?', 0), ('Is he from Australia?', 0), ('Is he from South America?', 0)],
    ('Is he from Canada?', 1):            [('Is he from the United States?', 0), ('Is he from Europe?', 0), ('Is he from Africa?', 0), ('Is he from Australia?', 0), ('Is he from South America?', 0)],
    ('Is he from Australia?', 1):         [('Is he from the United States?', 0), ('Is he from Europe?', 0), ('Is he from Africa?', 0), ('Is he from Canada?', 0), ('Is he from South America?', 0)],
    ('Is he from South America?', 1):     [('Is he from the United States?', 0), ('Is he from Europe?', 0), ('Is he from Africa?', 0), ('Is he from Canada?', 0), ('Is he from Australia?', 0)],
    ('Is he 7 feet or taller?', 1):         [('Is he 6-8 or taller?', 1)],
    ('Is he 6-8 or taller?', 0):            [('Is he 7 feet or taller?', 0)],
    ('Was he a lottery pick (top 14)?', 1): [('Was he a first-round pick?', 1), ('Was he undrafted?', 0)],
    ('Was he a first-round pick?', 1):      [('Was he undrafted?', 0)],
    ('Was he a first-round pick?', 0):      [('Was he a lottery pick (top 14)?', 0)],
    ('Was he undrafted?', 1):               [('Was he a first-round pick?', 0), ('Was he a lottery pick (top 14)?', 0)],
    ('Shoots 40%+ from three this season?', 1):         [('Shoots 35%+ from three this season?', 1)],
    ('Shoots 35%+ from three this season?', 0):         [('Shoots 40%+ from three?', 0)],
    ('Has he been an All-Star 3+ times?', 1): [('Has he been an All-Star?', 1)],
    ('Has he been an All-Star?', 0):          [('Has he been an All-Star 3+ times?', 0)],
    ('Has he won the MVP award?', 1):         [('Has he been an All-Star?', 1), ('Has he been All-NBA?', 1)],
    ('Has he won Defensive Player of the Year?', 1): [('Has he been an All-Star?', 1)],
}
 
JERSEY_QS = [
    'Is his jersey number less than 10?',
    'Is his jersey number between 10 and 19?',
    'Is his jersey number between 20 and 29?',
    'Is his jersey number 30 or higher?',
]
 
@st.cache_data
def load_dataset():
    cache_valid = (
        os.path.exists(CACHE_FILE)
        and (time.time() - os.path.getmtime(CACHE_FILE)) < CACHE_MAX_DAYS * 86400
    )
    if cache_valid:
        return pd.read_csv(CACHE_FILE)
    totals_df = leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON, season_type_all_star='Regular Season'
    ).get_data_frames()[0]
    bio_df = playerindex.PlayerIndex(season=SEASON).get_data_frames()[0]
    bio_df = bio_df.rename(columns={'PERSON_ID': 'PLAYER_ID'})
    bio_df['PLAYER_ID'] = bio_df['PLAYER_ID'].astype(int)
    bio_lookup = bio_df.set_index('PLAYER_ID')
    rows = []
    for _, row in totals_df.iterrows():
        gp = row['GP'] if row['GP'] > 0 else 1
        ppg, rpg, apg = row['PTS']/gp, row['REB']/gp, row['AST']/gp
        team = row.get('TEAM_ABBREVIATION', '')
        conference = TEAM_CONFERENCE.get(team, '')
        division = TEAM_DIVISION.get(team, '')
        pid = int(row['PLAYER_ID'])
        bio = bio_lookup.loc[pid] if pid in bio_lookup.index else {}
        def safe(key):
            v = bio.get(key, '') if isinstance(bio, dict) else (bio[key] if key in bio.index else '')
            return '' if pd.isna(v) else str(v).strip()
        school, country = safe('COLLEGE'), safe('COUNTRY')
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
            aw = playerawards.PlayerAwards(player_id=pid).get_data_frames()[0]
            descs = set(aw['DESCRIPTION'].tolist())
            all_star_count = int((aw['DESCRIPTION'] == 'All-Star').sum())
        except Exception:
            descs, all_star_count = set(), 0
        has_ring    = int('NBA Champion' in descs)
        has_allnba  = int('All-NBA' in descs)
        has_all_defense = int('All-Defensive Team' in descs)
        is_mvp      = int('Most Valuable Player' in descs)
        is_dpoy     = int('Defensive Player of the Year' in descs)
        is_allstar  = int(all_star_count > 0)
        is_3x_allstar = int(all_star_count >= 3)
        rows.append({
            'Player': row['PLAYER_NAME'],
            'PLAYER_ID': pid,
            'Averages 25+ PPG this season?': int(ppg >= 25), 'Averages 20+ PPG this season?': int(ppg >= 20),
            'Averages 15+ PPG this season?': int(ppg >= 15), 'Averages 10+ PPG this season?': int(ppg >= 10),
            'Averages 10+ RPG this season?': int(rpg >= 10), 'Averages 5+ RPG this season?': int(rpg >= 5),
            'Averages 7+ APG this season?': int(apg >= 7), 'Averages 4+ APG this season?': int(apg >= 4),
            'Averages 1.5+ SPG this season?': int(row['STL']/gp >= 1.5), 'Averages 1+ SPG this season?': int(row['STL']/gp >= 1),
            'Averages 1.5+ BPG this season?': int(row['BLK']/gp >= 1.5), 'Averages 1+ BPG this season?': int(row['BLK']/gp >= 1),
            'Averages 3+ 3PM this season?': int(row['FG3M']/gp >= 3), 'Averages 1+ 3PM this season?': int(row['FG3M']/gp >= 1),
            'Averages 30+ min per game this season?': int(row['MIN']/gp >= 30), 'Averages 20+ min per game this season?': int(row['MIN']/gp >= 20),
            'Shoots 50%+ from the field this season?': int(row['FG_PCT'] >= 0.50),
            'Shoots 35%+ from three this season?': int(row['FG3_PCT'] >= 0.35),
            'Shoots 80%+ from the line this season?': int(row['FT_PCT'] >= 0.80),
            'Averages 3+ offensive rebounds this season?': int(row['OREB']/gp >= 3),
            'Averages 3+ turnovers this season?': int(row['TOV']/gp >= 3),
            'Played 50+ games this season?': int(row['GP'] >= 50), 'Played 70+ games this season?': int(row['GP'] >= 70),
            'Plays in the Eastern Conference?': int(conference == 'East'), 'Plays in the Western Conference?': int(conference == 'West'),
            'Plays in the Atlantic Division?': int(division == 'Atlantic'), 'Plays in the Central Division?': int(division == 'Central'),
            'Plays in the Southeast Division?': int(division == 'Southeast'), 'Plays in the Northwest Division?': int(division == 'Northwest'),
            'Plays in the Pacific Division?': int(division == 'Pacific'), 'Plays in the Southwest Division?': int(division == 'Southwest'),
            'Is his jersey number less than 10?': int(0 <= jersey_num < 10),
            'Is his jersey number between 10 and 19?': int(10 <= jersey_num <= 19),
            'Is his jersey number between 20 and 29?': int(20 <= jersey_num <= 29),
            'Is his jersey number 30 or higher?': int(jersey_num >= 30),
            'Is his jersey number an odd number?': int(jersey_num >= 0 and jersey_num % 2 == 1),
            'Is he from the United States?': int(country in ('USA', 'United States')),
            'Is he from Europe?': int(country in EUROPE), 'Is he from Africa?': int(country in AFRICA),
            'Is he from Canada?': int(country == 'Canada'), 'Is he from Australia?': int(country in ('Australia', 'New Zealand')),
            'Is he from South America?': int(country in SOUTH_AMERICA),
            'Did he play college basketball?': int(bool(school) and school.upper() not in ('', 'NONE', 'N/A')),
            'MPG': round(row['MIN'] / gp, 2),
            'Is he 25 or younger?': int(0 < age <= 25),
            'Is he 30 or older?': int(age >= 30),
            'Is he 6-8 or taller?': int(height_inches >= 80),
            'Is he 7 feet or taller?': int(height_inches >= 84),
            'Was he a first-round pick?': is_first_round,
            'Was he a lottery pick (top 14)?': is_lottery,
            'Was he undrafted?': is_undrafted,
            'Averages 5+ APG?': int(apg >= 5),
            'Averages 8+ RPG?': int(rpg >= 8),
            'Shoots 40%+ from three?': int(row['FG3_PCT'] >= 0.40),
            'Does his last name start with A-M?': int(row['PLAYER_NAME'].split()[-1][0].upper() <= 'M'),
            'Does his first name start with A-M?': int(row['PLAYER_NAME'].split()[0][0].upper() <= 'M'),
            'Does his last name have more than 6 letters?': int(len(row['PLAYER_NAME'].split()[-1]) > 6),
            'Does his first name end in a vowel?': int(row['PLAYER_NAME'].split()[0][-1].upper() in 'AEIOU'),
            'Has he been an All-Star?': is_allstar,
            'Has he been an All-Star 3+ times?': is_3x_allstar,
            'Has he won an NBA Championship?': has_ring,
            'Has he been All-NBA?': has_allnba,
            'Has he won the MVP award?': is_mvp,
            'Has he won Defensive Player of the Year?': is_dpoy,
            'Has he made an All-Defensive Team?': has_all_defense,
            'Does he play for a 2026 playoff team?': int(team in PLAYOFF_TEAMS),
            'Has he scored 10,000+ career points?': int(row['PTS'] >= 10000),
            'Has he grabbed 5,000+ career rebounds?': int(row['REB'] >= 5000),
            'Has he dished 5,000+ career assists?': int(row['AST'] >= 5000),
            'Has he played for 3+ teams?': int(len(set(row['TEAM_ABBREVIATION'].split('-'))) >= 3),
            'Has he played for 10+ seasons?': int(seasons_played >= 10),
            'Has he ever averaged 30+ PPG in a season?': int((totals_df['PTS']/totals_df['GP'] >= 30).sum() >= 1),
        })
    df = pd.DataFrame(rows)
    df.to_csv(CACHE_FILE, index=False)
    return df
 
def apply_implication(known, q, v):
    known[q] = v
    for implied_q, implied_v in IMPLICATIONS.get((q, v), []):
        if implied_q not in known:
            known[implied_q] = implied_v
    jersey_nos = [jq for jq in JERSEY_QS if known.get(jq) == 0]
    if len(jersey_nos) == 3:
        remaining = [jq for jq in JERSEY_QS if jq not in jersey_nos][0]
        if remaining not in known:
            apply_implication(known, remaining, 1)
 
def refilter_candidates(df, known):
    """Filter the full dataset against every known answer.
    First pass: apply all constraints strictly.
    If that yields 0 results (player not in dataset), fall back to best-effort filtering.
    """
    candidates = df.copy()
    for q, v in known.items():
        if q in candidates.columns:
            candidates = candidates[candidates[q] == v]
    if len(candidates) > 0:
        return candidates
    # Fallback: apply filters one by one, skipping any that would eliminate all candidates
    candidates = df.copy()
    for q, v in known.items():
        if q in candidates.columns:
            filtered = candidates[candidates[q] == v]
            if len(filtered) > 0:
                candidates = filtered
    return candidates
 
def advance_to_next_question():
    s = st.session_state
    while s.q_idx < len(s.questions):
        q = s.questions[s.q_idx]
        s.q_idx += 1
        if s.question_count >= 20:
            break
        if q in s.known:
            continue
        s.current_question = q
        s.phase = 'asking'
        return
    make_final_guess()
 
def _weighted_pick(names, df):
    weights = []
    for p in names:
        mpg = df.loc[df['Player'] == p, 'MPG']
        weights.append(float(mpg.iloc[0]) if not mpg.empty else 1.0)
    return random.choices(names, weights=weights, k=1)[0]
 
def make_final_guess():
    s = st.session_state
    unguessed = [p for p in s.candidates['Player'] if p not in s.guessed]
    if not unguessed:
        unguessed = [p for p in s.df['Player'] if p not in s.guessed]
    if not unguessed:
        s.phase = 'lost'
        return
    s.current_guess = _weighted_pick(unguessed, s.df)
    s.guessed.append(s.current_guess)
    s.phase = 'guessing'
    s.is_final_guess = True
 
def init_game(df, feature_columns):
    s = st.session_state
    s.df = df  # store full df for refiltering
    s.candidates = df.copy()
    s.questions = random.sample(list(feature_columns), len(feature_columns))
    s.q_idx = 0
    s.question_count = 0
    s.next_guess_at = 5
    s.known = {}
    s.guessed = []
    s.phase = 'asking'
    s.current_question = None
    s.current_guess = None
    s.is_final_guess = False
    s.history = []
    s.prev_candidate_count = len(df)
    advance_to_next_question()
 
is_last=False
def on_question_answer(val):
    s = st.session_state
    q = s.current_question
    s.history.append((q, 'Yes' if val == 1 else 'No'))
    s.candidate_count_before = len(s.candidates)
    apply_implication(s.known, q, val)
    # Refilter against ALL known answers (including inferred ones)
    s.candidates = refilter_candidates(s.df, s.known)
    s.prev_candidate_count = getattr(s, 'candidate_count_before', len(s.df))
    s.question_count += 1
    is_last = s.question_count >= 20
 
    if is_last:
        make_final_guess()
    elif s.question_count >= s.next_guess_at:
        s.next_guess_at += 5
        unguessed = [p for p in s.candidates['Player'] if p not in s.guessed]
        if not unguessed:
            unguessed = [p for p in s.df['Player'] if p not in s.guessed]
        if unguessed:
            s.current_guess = _weighted_pick(unguessed, s.df)
            s.guessed.append(s.current_guess)
            s.phase = 'guessing'
            s.is_final_guess = False
            return
        advance_to_next_question()
    else:
        advance_to_next_question()
 
def on_guess_answer(correct):
    s = st.session_state
    if correct:
        s.phase = 'won'
        return

    remaining_candidates = [p for p in s.candidates['Player'] if p != s.current_guess]
    if getattr(s, 'is_final_guess', False) or len(remaining_candidates) == 0:
        s.phase = 'lost'
    else:
        advance_to_next_question()
 
# ── UI ──────────────────────────────────────────────────────────────────────
 
st.set_page_config(page_title="Who You Got?", page_icon="🏀", layout="centered")
st.title("🏀 Who You Got?")
st.subheader("An NBA player guessing game")
st.caption("Think of an active NBA player and I will try to guess who it is!")
st.markdown("**Deployed version: test-1**")
st.markdown("""
<style>
.info-icon {
    display: inline-block;
    width: 22px; height: 22px;
    background: #4a90d9;
    color: white;
    border-radius: 50%;
    font-size: 13px;
    font-weight: bold;
    text-align: center;
    line-height: 22px;
    cursor: default;
    position: relative;
}
.info-icon .tooltip {
    visibility: hidden;
    width: 280px;
    background: #333;
    color: #fff;
    font-size: 13px;
    font-weight: normal;
    border-radius: 6px;
    padding: 10px 12px;
    position: absolute;
    z-index: 999;
    top: 28px;
    left: 50%;
    transform: translateX(-50%);
    white-space: normal;
    line-height: 1.5;
}
.info-icon:hover .tooltip { visibility: visible; }
</style>
<div style="text-align:center; margin-top:-8px; margin-bottom:8px;">
  <span class="info-icon">i
    <span class="tooltip">
      <b>How to play:</b><br>
      1. Think of any active NBA player.<br>
      2. Answer yes or no to each question.<br>
      3. I'll make a guess every 5 questions.<br>
      4. You have 20 questions to stump me — good luck! 🏀<br>
         <i>(Data is from the 2025-26 season, so rookies and recent breakout players may be harder to guess!)</i>
    </span>
  </span>
</div>
""", unsafe_allow_html=True)
st.markdown("""
<style>
h1, h2, h3, .stImage, .stImage img, .stMarkdown, .stSuccess, .stAlert {
    text-align: center !important;
}
.stImage { display: flex; justify-content: center; align-items: center; }
.stImage img { margin: 0 auto; }
div[data-testid="column"] { display: flex; justify-content: center; }
</style>
""", unsafe_allow_html=True)
 
with st.spinner("Loading NBA player data..."):
    df = load_dataset()
feature_columns = [c for c in df.columns if c not in ('Player', 'PLAYER_ID', 'MPG')]
 
if 'phase' not in st.session_state:
    init_game(df, feature_columns)
 
s = st.session_state
 
# Progress bar
if s.phase in ('asking', 'guessing'):
    display_count = min(s.question_count, 20)
    st.progress(display_count / 20, text=f"Question {display_count} / 20")
    total = len(df)
    current = len(s.candidates) if s.get('candidates') is not None else total
    prev = s.get('prev_candidate_count', total)
    delta = current - prev
    col_m, col_b = st.columns([1, 2])
    col_m.metric("🎯 Players remaining", current, delta=delta, delta_color="inverse")
    col_b.progress(current / total, text=f"{current} of {total} players still possible")
 
# Question history
if s.get('history') or s.get('guessed'):
    with st.expander("Questions so far", expanded=False):
        for q, a in s.get('history', []):
            colour = "green" if a == "Yes" else "red"
            st.markdown(f"- {q} → :{colour}[**{a}**]")
        past_guesses = s.get('guessed', [])[:-1]  # exclude current guess
        if past_guesses:
            st.markdown("**Previous guesses:** " + ", ".join(f"~~{p}~~" for p in past_guesses))
 
st.divider()
 
if s.phase == 'asking' or is_last:
    st.subheader(f"Q{s.question_count + 1}: {s.current_question}")
    col1, col2 = st.columns(2)
    if col1.button("✅ Yes", use_container_width=True):
        on_question_answer(1)
        st.rerun()
    if col2.button("❌ No", use_container_width=True):
        on_question_answer(0)
        st.rerun()
 
elif s.phase == 'guessing':
    player_row = df[df['Player'] == s.current_guess]
    if not player_row.empty:
        pid = int(player_row.iloc[0]['PLAYER_ID'])
        photo_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png"
        with st.spinner("Loading photo..."):
            st.markdown(f'<div style="text-align: center;"><img src="{photo_url}" width="260" /></div>', unsafe_allow_html=True)
    st.subheader("I think you got…")
    st.markdown(f"## {s.current_guess}!")
    col1, col2 = st.columns(2)
    if col1.button("✅ Yes, that's them!", use_container_width=True):
        on_guess_answer(True)
        st.rerun()
    no_label = "❌ No, I win!" if s.is_final_guess else "❌ No, keep guessing"
    if col2.button(no_label, use_container_width=True):
        on_guess_answer(False)
        st.rerun()
 
elif s.phase == 'won':
    player_row = df[df['Player'] == s.current_guess]
    if not player_row.empty:
        pid = int(player_row.iloc[0]['PLAYER_ID'])
        with st.spinner("Loading photo..."):
            st.markdown(f'<div style="text-align: center;"><img src="https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png" width="260" /></div>', unsafe_allow_html=True)
    st.success(f"🎉 I got it — **{s.current_guess}**!")
    st.balloons()
    if st.button("Play again", use_container_width=True):
        init_game(df, feature_columns)
        st.rerun()
 
elif s.phase == 'lost':
    st.error("You win! I couldn't guess your player in 20 questions. 🏆")
    if st.button("Play again", use_container_width=True):
        init_game(df, feature_columns)
        st.rerun()