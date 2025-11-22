"""
Football Predictor using Football-Data.org API
Adapted for free tier with current season fixtures
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('predictor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
FOOTBALL_DATA_API_KEY = os.getenv('FOOTBALL_DATA_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not all([FOOTBALL_DATA_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing required environment variables")

BASE_URL = 'https://api.football-data.org/v4'

# Available competitions (free tier - 13 total)
COMPETITIONS = {
    # Top 5 European Leagues
    'PL': 2021,    # Premier League (England)
    'PD': 2014,    # La Liga (Spain)
    'SA': 2019,    # Serie A (Italy)
    'BL1': 2002,   # Bundesliga (Germany)
    'FL1': 2015,   # Ligue 1 (France)

    # Other European Leagues
    'DED': 2003,   # Eredivisie (Netherlands)
    'PPL': 2017,   # Primeira Liga (Portugal)
    'ELC': 2016,   # Championship (England)
    'BSA': 2013,   # Serie A (Brazil)

    # International Competitions
    'CL': 2001,    # UEFA Champions League
    'EC': 2018,    # European Championship (Euro)
    'WC': 2000,    # FIFA World Cup
    'CLI': 2021,   # Copa Libertadores
}


@dataclass
class TeamStats:
    """Team statistics"""
    form: str
    form_points: int
    goals_scored_avg: float
    goals_conceded_avg: float
    recent_form_weight: float


@dataclass
class MatchPrediction:
    """Match predictions"""
    home_win: int
    draw: int
    away_win: int
    over_05: int
    under_05: int
    over_15: int
    under_15: int
    over_25: int
    under_25: int
    over_35: int
    under_35: int
    over_45: int
    under_45: int
    over_55: int
    under_55: int
    over_65: int
    under_65: int
    over_75: int
    under_75: int
    over_85: int
    under_85: int
    over_95: int
    under_95: int
    btts: int
    confidence_score: float


class FootballDataPredictor:
    """Football prediction system using Football-Data.org"""

    def __init__(self):
        self.headers = {'X-Auth-Token': FOOTBALL_DATA_API_KEY}
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.session = self._create_session()
        self.weights = self.load_weights()
        logger.info("Predictor initialized successfully")

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def load_weights(self) -> Dict[str, float]:
        """Load prediction weights from database"""
        try:
            response = self.supabase.table('learning_weights').select('*').execute()
            weights = {w['factor_name']: float(w['current_weight']) for w in response.data}

            if not weights:
                weights = {
                    'form_points': 1.0,
                    'goals_scored_weight': 1.0,
                    'goals_conceded_weight': 1.0,
                    'home_advantage': 1.0,
                }

            logger.info(f"Loaded {len(weights)} weight factors")
            return weights
        except Exception as e:
            logger.error(f"Error loading weights: {e}")
            return {
                'form_points': 1.0,
                'goals_scored_weight': 1.0,
                'goals_conceded_weight': 1.0,
                'home_advantage': 1.0,
            }

    def fetch_upcoming_fixtures(self, competition: str = 'PL', days_ahead: int = 7) -> List[Dict]:
        """Fetch upcoming fixtures for a competition"""
        url = f"{BASE_URL}/competitions/{competition}/matches"
        params = {'status': 'SCHEDULED'}

        try:
            response = self.session.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            matches = data.get('matches', [])

            # Filter to next N days
            from datetime import timezone
            cutoff_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)
            filtered = []

            for match in matches:
                match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))
                if match_date <= cutoff_date:
                    filtered.append(match)

            logger.info(f"Fetched {len(filtered)} upcoming fixtures for {competition}")
            return filtered[:10]  # Limit to 10 to save API calls

        except Exception as e:
            logger.error(f"Error fetching fixtures: {e}")
            return []

    def fetch_team_matches(self, team_id: int, limit: int = 10, competition_id: Optional[int] = None) -> List[Dict]:
        """Fetch recent matches for a team, optionally filtered by competition"""
        url = f"{BASE_URL}/teams/{team_id}/matches"
        params = {'status': 'FINISHED', 'limit': limit}

        # Filter by competition for league matches (not for international tournaments)
        if competition_id:
            params['competitions'] = competition_id

        try:
            time.sleep(7)  # Rate limiting: 10 req/min = 6s minimum, using 7s to be safe
            response = self.session.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            matches = data.get('matches', [])
            return matches[:limit]

        except Exception as e:
            logger.error(f"Error fetching team {team_id} matches: {e}")
            return []

    def calculate_team_stats(self, matches: List[Dict], team_id: int) -> Optional[TeamStats]:
        """Calculate team statistics from recent matches"""
        if not matches or len(matches) < 3:
            logger.warning(f"Insufficient match data for team {team_id}")
            return None

        form = []
        goals_scored = []
        goals_conceded = []
        weighted_points = 0
        weights = [1.0, 0.9, 0.8, 0.7, 0.6]  # Recency weighting

        for i, match in enumerate(matches[:5]):
            score = match.get('score', {}).get('fullTime', {})
            home_id = match['homeTeam']['id']
            away_id = match['awayTeam']['id']

            home_score = score.get('home')
            away_score = score.get('away')

            if home_score is None or away_score is None:
                continue

            is_home = (home_id == team_id)
            team_score = home_score if is_home else away_score
            opp_score = away_score if is_home else home_score

            goals_scored.append(team_score)
            goals_conceded.append(opp_score)

            # Calculate result
            if team_score > opp_score:
                form.append('W')
                points = 3
            elif team_score == opp_score:
                form.append('D')
                points = 1
            else:
                form.append('L')
                points = 0

            weight = weights[i] if i < len(weights) else 0.5
            weighted_points += points * weight

        if not goals_scored:
            return None

        return TeamStats(
            form=''.join(form),
            form_points=form.count('W') * 3 + form.count('D'),
            goals_scored_avg=round(sum(goals_scored) / len(goals_scored), 2),
            goals_conceded_avg=round(sum(goals_conceded) / len(goals_conceded), 2),
            recent_form_weight=weighted_points
        )

    def calculate_predictions(self, home_stats: TeamStats, away_stats: TeamStats) -> MatchPrediction:
        """Calculate match predictions"""
        w = self.weights

        # Expected goals
        home_expected = (
            (home_stats.goals_scored_avg * w['goals_scored_weight']) +
            (away_stats.goals_conceded_avg * w['goals_conceded_weight'])
        ) / 2

        away_expected = (
            (away_stats.goals_scored_avg * w['goals_scored_weight']) +
            (home_stats.goals_conceded_avg * w['goals_conceded_weight'])
        ) / 2

        # Home advantage
        home_expected += (0.35 * w['home_advantage'])

        total_expected = home_expected + away_expected

        # Calculate Over/Under for all goal lines (0.5 to 9.5)
        goal_lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5]
        goal_line_predictions = {}

        for line in goal_lines:
            # Base calculation uses distance from expected total
            over_base = 50 + (total_expected - line) * 20
            over_pct = max(5, min(95, int(over_base)))

            # Store both over and under
            line_key = str(line).replace('.', '')
            goal_line_predictions[f'over_{line_key}'] = over_pct
            goal_line_predictions[f'under_{line_key}'] = 100 - over_pct

        # Match result
        form_diff = (home_stats.recent_form_weight - away_stats.recent_form_weight) * w['form_points']
        home_advantage = 8 * w['home_advantage']

        home_win = 40 + (form_diff * 2) + home_advantage
        away_win = 30 - (form_diff * 1.5)

        home_win = max(15, min(75, home_win))
        away_win = max(10, min(60, away_win))

        # Ensure probabilities sum to 100%
        total_prob = home_win + away_win
        if total_prob > 85:
            scale = 85 / total_prob
            home_win *= scale
            away_win *= scale

        draw = 100 - home_win - away_win
        draw = max(15, draw)

        # Normalize
        total = home_win + draw + away_win
        home_win = (home_win / total) * 100
        draw = (draw / total) * 100
        away_win = (away_win / total) * 100

        # BTTS
        btts_prob = (home_expected / 2.0) * (away_expected / 2.0) * 100
        btts = max(10, min(75, int(btts_prob)))

        # Confidence
        sample_quality = min(len(home_stats.form), 5) / 5
        form_clarity = abs(home_stats.recent_form_weight - away_stats.recent_form_weight) / 15
        confidence = (sample_quality * 0.6 + form_clarity * 0.4)

        return MatchPrediction(
            home_win=round(home_win),
            draw=round(draw),
            away_win=round(away_win),
            over_05=goal_line_predictions['over_05'],
            under_05=goal_line_predictions['under_05'],
            over_15=goal_line_predictions['over_15'],
            under_15=goal_line_predictions['under_15'],
            over_25=goal_line_predictions['over_25'],
            under_25=goal_line_predictions['under_25'],
            over_35=goal_line_predictions['over_35'],
            under_35=goal_line_predictions['under_35'],
            over_45=goal_line_predictions['over_45'],
            under_45=goal_line_predictions['under_45'],
            over_55=goal_line_predictions['over_55'],
            under_55=goal_line_predictions['under_55'],
            over_65=goal_line_predictions['over_65'],
            under_65=goal_line_predictions['under_65'],
            over_75=goal_line_predictions['over_75'],
            under_75=goal_line_predictions['under_75'],
            over_85=goal_line_predictions['over_85'],
            under_85=goal_line_predictions['under_85'],
            over_95=goal_line_predictions['over_95'],
            under_95=goal_line_predictions['under_95'],
            btts=btts,
            confidence_score=round(confidence, 2)
        )

    def store_prediction(self, match: Dict, predictions: MatchPrediction) -> None:
        """Store prediction in Supabase"""
        try:
            match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))

            prediction_data = {
                'fixture_id': match['id'],
                'match_date': match_date.date().isoformat(),
                'home_team': match['homeTeam']['name'],
                'away_team': match['awayTeam']['name'],
                'league_id': match['competition']['id'],
                'predicted_home_win_pct': predictions.home_win,
                'predicted_draw_pct': predictions.draw,
                'predicted_away_win_pct': predictions.away_win,
                'predicted_over_05_pct': predictions.over_05,
                'predicted_under_05_pct': predictions.under_05,
                'predicted_over_15_pct': predictions.over_15,
                'predicted_under_15_pct': predictions.under_15,
                'predicted_over_25_pct': predictions.over_25,
                'predicted_under_25_pct': predictions.under_25,
                'predicted_over_35_pct': predictions.over_35,
                'predicted_under_35_pct': predictions.under_35,
                'predicted_over_45_pct': predictions.over_45,
                'predicted_under_45_pct': predictions.under_45,
                'predicted_over_55_pct': predictions.over_55,
                'predicted_under_55_pct': predictions.under_55,
                'predicted_over_65_pct': predictions.over_65,
                'predicted_under_65_pct': predictions.under_65,
                'predicted_over_75_pct': predictions.over_75,
                'predicted_under_75_pct': predictions.under_75,
                'predicted_over_85_pct': predictions.over_85,
                'predicted_under_85_pct': predictions.under_85,
                'predicted_over_95_pct': predictions.over_95,
                'predicted_under_95_pct': predictions.under_95,
                'predicted_btts_pct': predictions.btts,
                'confidence_score': predictions.confidence_score,
                'created_at': datetime.now().isoformat()
            }

            self.supabase.table('predictions').upsert(
                prediction_data,
                on_conflict='fixture_id'
            ).execute()

            logger.info(f"Stored: {match['homeTeam']['shortName']} vs {match['awayTeam']['shortName']} (confidence: {predictions.confidence_score})")

        except Exception as e:
            logger.error(f"Error storing prediction: {e}")

    def run_predictions(self, competition: str = 'PL'):
        """Run predictions for a competition"""
        logger.info(f"="*60)
        logger.info(f"Starting predictions for {competition}")
        logger.info(f"="*60)

        # Fetch fixtures
        fixtures = self.fetch_upcoming_fixtures(competition, days_ahead=7)

        if not fixtures:
            logger.warning("No upcoming fixtures found")
            return

        logger.info(f"\nFound {len(fixtures)} upcoming fixtures\n")

        predictions_made = 0

        for fixture in fixtures:
            home_team = fixture['homeTeam']
            away_team = fixture['awayTeam']
            match_date = datetime.fromisoformat(fixture['utcDate'].replace('Z', '+00:00'))
            competition_id = fixture.get('competition', {}).get('id')

            logger.info(f"\n📊 {home_team['shortName']} vs {away_team['shortName']}")
            logger.info(f"   Date: {match_date.strftime('%Y-%m-%d %H:%M UTC')}")

            # Fetch team histories - filter by competition for league matches
            home_matches = self.fetch_team_matches(home_team['id'], competition_id=competition_id)
            away_matches = self.fetch_team_matches(away_team['id'], competition_id=competition_id)

            if not home_matches or not away_matches:
                logger.warning("   ⚠️  Insufficient match data, skipping")
                continue

            # Calculate stats
            home_stats = self.calculate_team_stats(home_matches, home_team['id'])
            away_stats = self.calculate_team_stats(away_matches, away_team['id'])

            if not home_stats or not away_stats:
                logger.warning("   ⚠️  Could not calculate stats, skipping")
                continue

            # Generate predictions
            predictions = self.calculate_predictions(home_stats, away_stats)

            # Display predictions
            logger.info(f"   Form: {home_stats.form} vs {away_stats.form}")
            logger.info(f"   Result: Home {predictions.home_win}% | Draw {predictions.draw}% | Away {predictions.away_win}%")
            logger.info(f"   Goals: O0.5 {predictions.over_05}% | O1.5 {predictions.over_15}% | O2.5 {predictions.over_25}% | O3.5 {predictions.over_35}%")
            logger.info(f"   BTTS: {predictions.btts}% | Confidence: {predictions.confidence_score}")

            # Store in database
            self.store_prediction(fixture, predictions)
            predictions_made += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Completed! Made {predictions_made} predictions")
        logger.info(f"{'='*60}")


def main():
    """Main entry point"""
    import sys

    try:
        predictor = FootballDataPredictor()

        # Get competition from command line or default to Premier League
        competition = sys.argv[1] if len(sys.argv) > 1 else 'PL'

        if competition not in COMPETITIONS:
            logger.warning(f"Unknown competition '{competition}'. Using 'PL'")
            logger.info(f"Available: {', '.join(COMPETITIONS.keys())}")
            competition = 'PL'

        predictor.run_predictions(competition)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
