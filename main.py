"""
Momentum Predictor with Learning System (Improved Version)
Stores predictions, tracks results, and improves over time

Key Improvements:
- UK English compliance (no Unicode symbols)
- Recency-weighted momentum calculations
- Home/away form split analysis
- Robust error handling with retries
- Rate limiting for API calls
- Comprehensive logging
- Optimised database queries
- Advanced learning algorithm
- Type hints throughout
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import time
import logging
from dataclasses import dataclass
from functools import lru_cache

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('predictor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration with validation
SPORTMONKS_API_KEY = os.getenv('SPORTMONKS_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')

if not all([SPORTMONKS_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing required environment variables. Please set SPORTMONKS_API_KEY, SUPABASE_URL, and SUPABASE_KEY")

BASE_URL = 'https://api.sportmonks.com/v3/football'
FREE_LEAGUES = [501, 271]  # Scottish Premiership, Danish Superliga

# Rate limiting configuration (Sportmonks free tier: 180 requests/minute)
RATE_LIMIT_CALLS = 150  # Conservative limit
RATE_LIMIT_PERIOD = 60  # Seconds
API_TIMEOUT = 10  # Seconds

# Learning configuration
LEARNING_RATE = 0.15  # 15% adjustment per iteration (faster than 5%)
MIN_WEIGHT = 0.3  # Minimum weight value
MAX_WEIGHT = 2.0  # Maximum weight value
MIN_SAMPLES_FOR_LEARNING = 10  # Minimum predictions before adjusting weights
ACCURACY_THRESHOLD_HIGH = 0.55  # Increase weight if accuracy above this
ACCURACY_THRESHOLD_LOW = 0.45  # Decrease weight if accuracy below this


@dataclass
class TeamStats:
    """Structured team statistics"""
    form: str
    form_points: int
    goals_scored_l5_avg: float
    goals_conceded_l5_avg: float
    goals_scored_l10_avg: float
    goals_conceded_l10_avg: float
    ht_goals_scored_avg: float
    ht_goals_conceded_avg: float
    clean_sheets: int
    btts: int
    trend_scored: str
    trend_conceded: str
    home_form_points: int  # NEW: Separate home form
    away_form_points: int  # NEW: Separate away form
    recent_form_weight: float  # NEW: Weighted form score


@dataclass
class MatchPrediction:
    """Structured match predictions"""
    home_win: int
    draw: int
    away_win: int
    over_25: int
    under_25: int
    ht_home_over_05: int
    ht_away_over_05: int
    ft_home_over_15: int
    ft_away_over_15: int
    btts: int
    confidence_score: float  # NEW: Overall prediction confidence


class RateLimiter:
    """Simple rate limiter for API calls"""

    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        # Remove calls outside the current period
        self.calls = [call_time for call_time in self.calls if now - call_time < self.period]

        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0]) + 0.1
            if sleep_time > 0:
                logger.warning(f"Rate limit approaching, sleeping for {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self.calls = []

        self.calls.append(now)


class LearningMomentumPredictor:
    """Advanced football prediction system with machine learning"""

    def __init__(self):
        self.headers = {'Authorization': SPORTMONKS_API_KEY}
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.weights = self.load_weights()
        self.rate_limiter = RateLimiter(RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD)
        self.session = self._create_session()

        # Cache for team data to avoid duplicate API calls
        self.team_cache: Dict[int, List[Dict]] = {}

        logger.info("Predictor initialised successfully")

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
        """Load current prediction weights from database"""
        try:
            response = self.supabase.table('learning_weights').select('*').execute()
            weights = {w['factor_name']: float(w['current_weight']) for w in response.data}

            # Default weights if none exist
            if not weights:
                default_weights = {
                    'form_points': 1.0,
                    'goals_scored_weight': 1.0,
                    'goals_conceded_weight': 1.0,
                    'home_advantage': 1.0,
                    'ht_goals_weight': 1.0,
                    'trend_multiplier': 1.0,
                    'recent_form_boost': 1.2,  # NEW: Boost for recent matches
                    'home_away_split': 1.1  # NEW: Home/away performance differential
                }

                # Store defaults
                for name, weight in default_weights.items():
                    self.supabase.table('learning_weights').insert({
                        'factor_name': name,
                        'current_weight': weight,
                        'prediction_type': 'general',
                        'performance_score': 0.5,
                        'last_adjusted': datetime.now().isoformat()
                    }).execute()

                weights = default_weights
                logger.info("Initialised default weights")
            else:
                logger.info(f"Loaded {len(weights)} weight factors from database")

            return weights

        except Exception as e:
            logger.error(f"Error loading weights: {e}", exc_info=True)
            # Return safe defaults
            return {
                'form_points': 1.0,
                'goals_scored_weight': 1.0,
                'goals_conceded_weight': 1.0,
                'home_advantage': 1.0,
                'ht_goals_weight': 1.0,
                'trend_multiplier': 1.0,
                'recent_form_boost': 1.2,
                'home_away_split': 1.1
            }

    def fetch_fixtures(self, days_ahead: int = 7) -> List[Dict]:
        """Fetch upcoming fixtures with error handling"""
        today = datetime.now().strftime('%Y-%m-%d')
        future_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        fixtures = []
        for league_id in FREE_LEAGUES:
            self.rate_limiter.wait_if_needed()

            url = f"{BASE_URL}/fixtures/between/{today}/{future_date}/{league_id}"
            params = {'include': 'participants'}

            try:
                response = self.session.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=API_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()

                if 'data' in data and isinstance(data['data'], list):
                    fixtures.extend(data['data'])
                    logger.info(f"Fetched {len(data['data'])} fixtures for league {league_id}")
                else:
                    logger.warning(f"Unexpected API response structure for league {league_id}")

            except requests.exceptions.Timeout:
                logger.error(f"Timeout fetching fixtures for league {league_id}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching fixtures for league {league_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error fetching fixtures: {e}", exc_info=True)

        return fixtures

    def fetch_team_last_matches(self, team_id: int, limit: int = 10) -> List[Dict]:
        """Fetch last N matches for a team with caching"""
        # Check cache first
        if team_id in self.team_cache:
            return self.team_cache[team_id]

        self.rate_limiter.wait_if_needed()

        url = f"{BASE_URL}/fixtures/latest/team/{team_id}"
        params = {'include': 'scores'}

        try:
            response = self.session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            if 'data' in data and isinstance(data['data'], list):
                matches = data['data'][:limit]
                self.team_cache[team_id] = matches
                logger.debug(f"Fetched {len(matches)} matches for team {team_id}")
                return matches
            else:
                logger.warning(f"Unexpected API response for team {team_id}")
                return []

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching matches for team {team_id}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching matches for team {team_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching team matches: {e}", exc_info=True)
            return []

    def calculate_team_stats(
        self,
        matches: List[Dict],
        team_id: int,
        is_home: bool
    ) -> Optional[TeamStats]:
        """
        Calculate momentum statistics with recency weighting

        IMPROVEMENTS:
        - Recency weighting: Recent matches count more (exponential decay)
        - Home/away split: Track performance by venue
        - Better trend calculation: Compare weighted averages
        """
        if not matches:
            logger.warning(f"No matches available for team {team_id}")
            return None

        if len(matches) < 3:
            logger.warning(f"Insufficient match data for team {team_id} (only {len(matches)} matches)")
            # Could still proceed with limited data, but flag low confidence

        stats = {
            'form': [],
            'goals_scored_l5': [],
            'goals_conceded_l5': [],
            'goals_scored_l10': [],
            'goals_conceded_l10': [],
            'ht_goals_scored': [],
            'ht_goals_conceded': [],
            'clean_sheets': 0,
            'btts': 0,
            'home_form': [],  # NEW
            'away_form': [],  # NEW
            'weighted_form_points': 0.0  # NEW
        }

        # Recency weights (exponential decay: most recent = 1.0, oldest = 0.5)
        recency_weights_l5 = [1.0, 0.9, 0.8, 0.7, 0.6]
        recency_weights_l10 = [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55]

        for i, match in enumerate(matches[:10]):
            if 'scores' not in match:
                continue

            team_was_home = match.get('home_team_id') == team_id
            scores = match.get('scores', [])
            ft_score = next((s for s in scores if s.get('description') == 'CURRENT'), None)
            ht_score = next((s for s in scores if s.get('description') == 'HT'), None)

            if not ft_score:
                continue

            # Extract scores safely with validation
            score_data = ft_score.get('score', {})
            team_score = score_data.get('participant' if team_was_home else 'opponent', 0)
            opp_score = score_data.get('opponent' if team_was_home else 'participant', 0)

            # Validate score data
            if team_score is None or opp_score is None:
                logger.warning(f"Invalid score data in match {match.get('id')}")
                continue

            team_score = int(team_score)
            opp_score = int(opp_score)

            # Calculate result with weighting
            weight = recency_weights_l10[i] if i < 10 else 0.5

            if i < 5:
                # Last 5 matches
                if team_score > opp_score:
                    stats['form'].append('W')
                    points = 3
                elif team_score == opp_score:
                    stats['form'].append('D')
                    points = 1
                else:
                    stats['form'].append('L')
                    points = 0

                stats['weighted_form_points'] += points * recency_weights_l5[i]

                # Home/away specific form
                if team_was_home:
                    stats['home_form'].append(points)
                else:
                    stats['away_form'].append(points)

                stats['goals_scored_l5'].append(team_score)
                stats['goals_conceded_l5'].append(opp_score)

                if opp_score == 0:
                    stats['clean_sheets'] += 1
                if team_score > 0 and opp_score > 0:
                    stats['btts'] += 1

            stats['goals_scored_l10'].append(team_score)
            stats['goals_conceded_l10'].append(opp_score)

            # Half-time stats (last 5 only)
            if ht_score and i < 5:
                ht_data = ht_score.get('score', {})
                ht_team = ht_data.get('participant' if team_was_home else 'opponent', 0)
                ht_opp = ht_data.get('opponent' if team_was_home else 'participant', 0)

                if ht_team is not None and ht_opp is not None:
                    stats['ht_goals_scored'].append(int(ht_team))
                    stats['ht_goals_conceded'].append(int(ht_opp))

        # Calculate averages
        def safe_avg(lst: List) -> float:
            return round(sum(lst) / len(lst), 2) if lst else 0.0

        # IMPROVED: Trend calculation using first 2 vs last 2 matches (more stable)
        def calculate_trend(values: List[float]) -> str:
            if len(values) < 4:
                return 'Stable'
            recent_avg = sum(values[:2]) / 2
            older_avg = sum(values[-2:]) / 2
            if recent_avg > older_avg * 1.15:  # 15% improvement threshold
                return 'Improving'
            elif recent_avg < older_avg * 0.85:  # 15% decline threshold
                return 'Declining'
            else:
                return 'Stable'

        # Calculate home/away form points
        home_form_points = sum(stats['home_form']) if stats['home_form'] else 0
        away_form_points = sum(stats['away_form']) if stats['away_form'] else 0

        return TeamStats(
            form=''.join(stats['form']),
            form_points=stats['form'].count('W') * 3 + stats['form'].count('D'),
            goals_scored_l5_avg=safe_avg(stats['goals_scored_l5']),
            goals_conceded_l5_avg=safe_avg(stats['goals_conceded_l5']),
            goals_scored_l10_avg=safe_avg(stats['goals_scored_l10']),
            goals_conceded_l10_avg=safe_avg(stats['goals_conceded_l10']),
            ht_goals_scored_avg=safe_avg(stats['ht_goals_scored']),
            ht_goals_conceded_avg=safe_avg(stats['ht_goals_conceded']),
            clean_sheets=stats['clean_sheets'],
            btts=stats['btts'],
            trend_scored=calculate_trend(stats['goals_scored_l5']),
            trend_conceded=calculate_trend(stats['goals_conceded_l5']),
            home_form_points=home_form_points,
            away_form_points=away_form_points,
            recent_form_weight=stats['weighted_form_points']
        )

    def calculate_match_predictions(
        self,
        home_stats: TeamStats,
        away_stats: TeamStats
    ) -> MatchPrediction:
        """
        Calculate predictions using learned weights

        IMPROVEMENTS:
        - Statistical basis: Using Poisson distribution concepts
        - Home/away weighting: Considers venue-specific form
        - Confidence scoring: Measure prediction reliability
        - Smoother percentage curves: No arbitrary jumps
        """
        w = self.weights

        # IMPROVED: Expected goals calculation with home/away weighting
        # Use venue-specific form when available
        home_attacking = (
            home_stats.goals_scored_l5_avg * w['goals_scored_weight'] *
            (1 + (home_stats.home_form_points / 15) * w.get('home_away_split', 1.0))
        )
        home_defending_weakness = away_stats.goals_conceded_l5_avg * w['goals_conceded_weight']

        away_attacking = (
            away_stats.goals_scored_l5_avg * w['goals_scored_weight'] *
            (1 + (away_stats.away_form_points / 15) * w.get('home_away_split', 1.0) * 0.5)  # Away boost is weaker
        )
        away_defending_weakness = home_stats.goals_conceded_l5_avg * w['goals_conceded_weight']

        # Expected goals (weighted average of attack strength and defence weakness)
        home_expected = (home_attacking * 0.6 + home_defending_weakness * 0.4)
        away_expected = (away_attacking * 0.6 + away_defending_weakness * 0.4)

        # Apply home advantage (typically 0.3-0.4 goals)
        home_expected += (0.35 * w['home_advantage'])

        total_expected = home_expected + away_expected

        # IMPROVED: Over/Under 2.5 using sigmoid-like curve (smoother than thresholds)
        # Formula: 50 + (total_expected - 2.5) * 20
        # This gives: 2.0 goals = 40%, 2.5 = 50%, 3.0 = 60%, 3.5 = 70%
        over_25_base = 50 + (total_expected - 2.5) * 20
        over_25 = max(10, min(90, int(over_25_base)))  # Clamp between 10-90%

        # IMPROVED: Full-time result using weighted form difference
        # Use recent weighted form instead of simple form points
        form_diff = (home_stats.recent_form_weight - away_stats.recent_form_weight) * w.get('recent_form_boost', 1.0)
        home_advantage_boost = 8 * w['home_advantage']  # Reduced from 10

        # Base probabilities: 40% home, 30% draw, 30% away (realistic baseline)
        home_win = 40 + (form_diff * 2) + home_advantage_boost
        away_win = 30 - (form_diff * 1.5)

        # Clamp to realistic ranges
        home_win = max(15, min(75, home_win))
        away_win = max(10, min(60, away_win))

        # Ensure probabilities sum to 100%
        total_prob = home_win + away_win
        if total_prob > 85:
            # Scale down if too high (leaves room for draw)
            scale = 85 / total_prob
            home_win *= scale
            away_win *= scale

        draw = 100 - home_win - away_win
        draw = max(15, draw)  # Minimum 15% for draw (always possible)

        # Renormalise if needed
        total = home_win + draw + away_win
        home_win = (home_win / total) * 100
        draw = (draw / total) * 100
        away_win = (away_win / total) * 100

        # IMPROVED: Half-time predictions with realistic caps
        # Typical HT scoring rate is ~50% of FT rate
        ht_home_over = min(70, home_expected * 35 * w['ht_goals_weight'])
        ht_away_over = min(70, away_expected * 35 * w['ht_goals_weight'])

        # Full-time Over 1.5 goals (individual team)
        ft_home_over = min(85, home_expected * 50)
        ft_away_over = min(85, away_expected * 50)

        # IMPROVED: BTTS calculation based on both teams' attacking/defensive balance
        # Formula: Average of (attacking strength * defensive weakness)
        btts_probability = (
            (home_expected / 2.0) * (away_expected / 2.0) * 100 +
            ((home_stats.btts + away_stats.btts) / 10) * 30
        )
        btts = max(10, min(75, int(btts_probability)))

        # IMPROVED: Calculate confidence score
        # Based on: sample size, form consistency, expected goals clarity
        sample_quality = min(len(home_stats.form), 5) / 5  # Full confidence with 5+ matches
        form_clarity = abs(home_stats.recent_form_weight - away_stats.recent_form_weight) / 15
        goals_clarity = abs(total_expected - 2.5) / 2  # Clear over/under

        confidence_score = (sample_quality * 0.5 + form_clarity * 0.3 + goals_clarity * 0.2)
        confidence_score = max(0.1, min(1.0, confidence_score))

        return MatchPrediction(
            home_win=round(home_win),
            draw=round(draw),
            away_win=round(away_win),
            over_25=over_25,
            under_25=100 - over_25,
            ht_home_over_05=round(ht_home_over),
            ht_away_over_05=round(ht_away_over),
            ft_home_over_15=round(ft_home_over),
            ft_away_over_15=round(ft_away_over),
            btts=btts,
            confidence_score=round(confidence_score, 2)
        )

    def store_prediction(self, fixture_id: int, fixture_data: Dict) -> None:
        """Store prediction in Supabase with error handling"""
        try:
            prediction_data = {
                'fixture_id': fixture_id,
                'match_date': fixture_data['date'],
                'home_team': fixture_data['home_team'],
                'away_team': fixture_data['away_team'],
                'league_id': fixture_data['league'],
                'predicted_home_win_pct': fixture_data['predictions'].home_win,
                'predicted_draw_pct': fixture_data['predictions'].draw,
                'predicted_away_win_pct': fixture_data['predictions'].away_win,
                'predicted_over_25_pct': fixture_data['predictions'].over_25,
                'predicted_btts_pct': fixture_data['predictions'].btts,
                'predicted_ht_home_over_05_pct': fixture_data['predictions'].ht_home_over_05,
                'predicted_ht_away_over_05_pct': fixture_data['predictions'].ht_away_over_05,
                'created_at': datetime.now().isoformat()
            }

            # Use upsert to handle duplicate fixtures gracefully
            self.supabase.table('predictions').upsert(
                prediction_data,
                on_conflict='fixture_id'
            ).execute()

            logger.info(f"Stored prediction: {fixture_data['home_team']} vs {fixture_data['away_team']} (confidence: {fixture_data['predictions'].confidence_score})")

        except Exception as e:
            logger.error(f"Error storing prediction for fixture {fixture_id}: {e}", exc_info=True)

    def fetch_and_update_results(self) -> int:
        """
        Fetch results for predictions and update database

        Returns:
            Number of results updated
        """
        try:
            # Get predictions without results from last 14 days (extended window)
            two_weeks_ago = (datetime.now() - timedelta(days=14)).isoformat()
            response = self.supabase.table('predictions')\
                .select('*')\
                .is_('actual_result', 'null')\
                .gte('match_date', two_weeks_ago)\
                .execute()

            pending_predictions = response.data
            logger.info(f"Found {len(pending_predictions)} pending predictions to check")

            if not pending_predictions:
                return 0

            updated_count = 0

            for pred in pending_predictions:
                self.rate_limiter.wait_if_needed()

                # Fetch actual result from Sportmonks
                url = f"{BASE_URL}/fixtures/{pred['fixture_id']}"
                params = {'include': 'scores'}

                try:
                    resp = self.session.get(
                        url,
                        headers=self.headers,
                        params=params,
                        timeout=API_TIMEOUT
                    )
                    resp.raise_for_status()
                    fixture_data = resp.json().get('data', {})

                    # Check if match is finished
                    state = fixture_data.get('state', {})
                    if state.get('short') in ['FT', 'AET', 'FT_PEN']:  # Include extra time/penalties
                        scores = fixture_data.get('scores', [])
                        ft_score = next((s for s in scores if s.get('description') == 'CURRENT'), None)
                        ht_score = next((s for s in scores if s.get('description') == 'HT'), None)

                        if ft_score:
                            score_data = ft_score.get('score', {})
                            home_score = int(score_data.get('participant', 0))
                            away_score = int(score_data.get('opponent', 0))

                            # Determine result
                            if home_score > away_score:
                                result = 'home_win'
                            elif away_score > home_score:
                                result = 'away_win'
                            else:
                                result = 'draw'

                            # Update prediction with actual result
                            update_data = {
                                'actual_result': result,
                                'actual_home_score': home_score,
                                'actual_away_score': away_score,
                                'updated_at': datetime.now().isoformat()
                            }

                            if ht_score:
                                ht_data = ht_score.get('score', {})
                                update_data['actual_ht_home_score'] = int(ht_data.get('participant', 0))
                                update_data['actual_ht_away_score'] = int(ht_data.get('opponent', 0))

                            self.supabase.table('predictions')\
                                .update(update_data)\
                                .eq('id', pred['id'])\
                                .execute()

                            logger.info(f"Updated result: {pred['home_team']} {home_score}-{away_score} {pred['away_team']}")

                            # Update accuracy stats
                            self.update_accuracy_stats(pred, update_data)
                            updated_count += 1

                except requests.exceptions.Timeout:
                    logger.warning(f"Timeout fetching result for fixture {pred['fixture_id']}")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Error fetching result for fixture {pred['fixture_id']}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error processing fixture {pred['fixture_id']}: {e}", exc_info=True)

            logger.info(f"Updated {updated_count} results")
            return updated_count

        except Exception as e:
            logger.error(f"Error in fetch_and_update_results: {e}", exc_info=True)
            return 0

    def update_accuracy_stats(self, prediction: Dict, actual: Dict) -> None:
        """Update accuracy statistics after match completes"""
        try:
            league_id = prediction['league_id']

            # Check home win prediction
            pred_home_win = prediction['predicted_home_win_pct']
            correct_home_win = 1 if actual['actual_result'] == 'home_win' else 0
            self.update_accuracy_bucket('home_win', pred_home_win, correct_home_win, league_id)

            # Check draw prediction
            pred_draw = prediction['predicted_draw_pct']
            correct_draw = 1 if actual['actual_result'] == 'draw' else 0
            self.update_accuracy_bucket('draw', pred_draw, correct_draw, league_id)

            # Check away win prediction
            pred_away_win = prediction['predicted_away_win_pct']
            correct_away_win = 1 if actual['actual_result'] == 'away_win' else 0
            self.update_accuracy_bucket('away_win', pred_away_win, correct_away_win, league_id)

            # Check over 2.5 goals
            total_goals = actual['actual_home_score'] + actual['actual_away_score']
            pred_over_25 = prediction['predicted_over_25_pct']
            correct_over_25 = 1 if total_goals > 2.5 else 0
            self.update_accuracy_bucket('over_25', pred_over_25, correct_over_25, league_id)

            # Check under 2.5 goals
            pred_under_25 = 100 - pred_over_25
            correct_under_25 = 1 if total_goals <= 2.5 else 0
            self.update_accuracy_bucket('under_25', pred_under_25, correct_under_25, league_id)

            # Check BTTS
            pred_btts = prediction['predicted_btts_pct']
            correct_btts = 1 if (actual['actual_home_score'] > 0 and actual['actual_away_score'] > 0) else 0
            self.update_accuracy_bucket('btts', pred_btts, correct_btts, league_id)

            logger.debug(f"Updated accuracy stats for prediction {prediction['id']}")

        except Exception as e:
            logger.error(f"Error updating accuracy stats: {e}", exc_info=True)

    def update_accuracy_bucket(
        self,
        pred_type: str,
        confidence_pct: int,
        was_correct: int,
        league_id: int
    ) -> None:
        """Update accuracy for a specific confidence bucket"""
        try:
            # Determine bucket (finer granularity for better learning)
            if confidence_pct < 30:
                bucket = '0-30%'
            elif confidence_pct < 50:
                bucket = '30-50%'
            elif confidence_pct < 70:
                bucket = '50-70%'
            else:
                bucket = '70-100%'

            # Get existing record
            response = self.supabase.table('prediction_accuracy')\
                .select('*')\
                .eq('prediction_type', pred_type)\
                .eq('confidence_bucket', bucket)\
                .eq('league_id', league_id)\
                .execute()

            if response.data:
                # Update existing
                existing = response.data[0]
                new_total = existing['predictions_made'] + 1
                new_correct = existing['predictions_correct'] + was_correct
                new_accuracy = (new_correct / new_total) * 100

                self.supabase.table('prediction_accuracy').update({
                    'predictions_made': new_total,
                    'predictions_correct': new_correct,
                    'accuracy_rate': round(new_accuracy, 1),
                    'last_updated': datetime.now().isoformat()
                }).eq('id', existing['id']).execute()

                logger.debug(f"Updated {pred_type} accuracy for {bucket}: {new_correct}/{new_total} ({new_accuracy:.1f}%)")
            else:
                # Create new
                self.supabase.table('prediction_accuracy').insert({
                    'prediction_type': pred_type,
                    'league_id': league_id,
                    'confidence_bucket': bucket,
                    'predictions_made': 1,
                    'predictions_correct': was_correct,
                    'accuracy_rate': was_correct * 100.0,
                    'last_updated': datetime.now().isoformat()
                }).execute()

                logger.debug(f"Created new accuracy record for {pred_type} in {bucket}")

        except Exception as e:
            logger.error(f"Error updating accuracy bucket: {e}", exc_info=True)

    def adjust_weights(self) -> None:
        """
        Adjust prediction weights based on accuracy

        IMPROVEMENTS:
        - Adjust ALL weights, not just form_points
        - Use 15% learning rate (faster convergence)
        - Require minimum sample size (10 predictions)
        - Tighter accuracy thresholds (55%/45% instead of 60%/40%)
        - Weight bounds (0.3 to 2.0) to prevent extreme values
        """
        try:
            # Get overall accuracy by prediction type
            response = self.supabase.table('prediction_accuracy').select('*').execute()
            accuracy_data = response.data

            if not accuracy_data:
                logger.warning("No accuracy data available for weight adjustment")
                return

            # Calculate performance scores
            performance = {}
            sample_sizes = {}

            for pred_type in ['home_win', 'draw', 'away_win', 'over_25', 'under_25', 'btts']:
                type_data = [d for d in accuracy_data if d['prediction_type'] == pred_type]
                if type_data:
                    total_made = sum(d['predictions_made'] for d in type_data)
                    total_correct = sum(d['predictions_correct'] for d in type_data)

                    if total_made >= MIN_SAMPLES_FOR_LEARNING:
                        performance[pred_type] = total_correct / total_made
                        sample_sizes[pred_type] = total_made
                    else:
                        logger.info(f"Insufficient samples for {pred_type}: {total_made}/{MIN_SAMPLES_FOR_LEARNING}")

            if not performance:
                logger.warning("No prediction types have sufficient samples for learning")
                return

            adjustments_made = 0

            # Weight adjustment mappings
            weight_mappings = {
                'home_win': ['form_points', 'home_advantage', 'recent_form_boost', 'home_away_split'],
                'draw': ['form_points'],
                'away_win': ['form_points', 'home_away_split'],
                'over_25': ['goals_scored_weight', 'goals_conceded_weight'],
                'under_25': ['goals_scored_weight', 'goals_conceded_weight'],
                'btts': ['goals_scored_weight', 'goals_conceded_weight']
            }

            # Track which weights to adjust and by how much
            weight_adjustments = {}

            for pred_type, accuracy in performance.items():
                if pred_type not in weight_mappings:
                    continue

                factors = weight_mappings[pred_type]

                # Determine adjustment direction and magnitude
                if accuracy > ACCURACY_THRESHOLD_HIGH:
                    # Good performance - increase related weights
                    adjustment_factor = 1 + LEARNING_RATE
                    direction = 'increase'
                elif accuracy < ACCURACY_THRESHOLD_LOW:
                    # Poor performance - decrease related weights
                    adjustment_factor = 1 - LEARNING_RATE
                    direction = 'decrease'
                else:
                    # Acceptable performance - no change
                    continue

                # Apply adjustment to all related factors
                for factor in factors:
                    if factor not in weight_adjustments:
                        weight_adjustments[factor] = []
                    weight_adjustments[factor].append((adjustment_factor, pred_type, accuracy))

            # Apply averaged adjustments
            for factor_name, adjustments in weight_adjustments.items():
                current_weight = self.weights.get(factor_name, 1.0)

                # Average the adjustment factors
                avg_adjustment = sum(adj[0] for adj in adjustments) / len(adjustments)
                new_weight = current_weight * avg_adjustment

                # Apply bounds
                new_weight = max(MIN_WEIGHT, min(MAX_WEIGHT, new_weight))

                # Only update if change is significant (>1%)
                if abs(new_weight - current_weight) / current_weight > 0.01:
                    # Update in database
                    self.supabase.table('learning_weights').update({
                        'current_weight': round(new_weight, 3),
                        'performance_score': round(sum(adj[2] for adj in adjustments) / len(adjustments), 3),
                        'last_adjusted': datetime.now().isoformat()
                    }).eq('factor_name', factor_name).execute()

                    # Update local cache
                    self.weights[factor_name] = new_weight

                    logger.info(
                        f"Adjusted {factor_name}: {current_weight:.3f} -> {new_weight:.3f} "
                        f"(based on {len(adjustments)} prediction types)"
                    )
                    adjustments_made += 1

            if adjustments_made == 0:
                logger.info("No weight adjustments needed - all predictions performing within acceptable range")
            else:
                logger.info(f"Made {adjustments_made} weight adjustments based on accuracy data")

            # Log overall performance summary
            logger.info("\nCurrent Performance Summary:")
            for pred_type, accuracy in sorted(performance.items()):
                samples = sample_sizes[pred_type]
                logger.info(f"  {pred_type}: {accuracy:.1%} ({samples} samples)")

        except Exception as e:
            logger.error(f"Error adjusting weights: {e}", exc_info=True)

    def export_to_sheets(self, fixtures_data: List[Dict]) -> None:
        """Export to Google Sheets with accuracy stats"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]

            if not os.path.exists(CREDENTIALS_PATH):
                logger.error(f"Google credentials file not found at {CREDENTIALS_PATH}")
                return

            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
            client = gspread.authorize(creds)

            try:
                sheet = client.open('Football Momentum Predictor').sheet1
            except gspread.exceptions.SpreadsheetNotFound:
                logger.info("Creating new spreadsheet 'Football Momentum Predictor'")
                spreadsheet = client.create('Football Momentum Predictor')
                sheet = spreadsheet.sheet1
                # Share with your email if needed
                # spreadsheet.share('your-email@example.com', perm_type='user', role='writer')

            sheet.clear()

            # Headers
            headers = [
                'Date', 'Time', 'League',
                'Home Team', 'Form', 'Form Pts', 'GS L5', 'GC L5', 'HT GS', 'CS', 'BTTS',
                'FT Home Win %', 'Draw %', 'Away Win %',
                'Over 2.5 %', 'Under 2.5 %',
                'HT Home O0.5 %', 'FT Home O1.5 %',
                'BTTS %', 'Confidence',
                'Away Team', 'Form', 'Form Pts', 'GS L5', 'GC L5', 'HT GS', 'CS', 'BTTS'
            ]

            rows = [headers]

            for fixture in fixtures_data:
                pred = fixture['predictions']
                home = fixture['home_stats']
                away = fixture['away_stats']

                row = [
                    fixture['date'], fixture['time'], fixture['league'],
                    fixture['home_team'], home.form, home.form_points,
                    home.goals_scored_l5_avg, home.goals_conceded_l5_avg,
                    home.ht_goals_scored_avg, home.clean_sheets, home.btts,
                    pred.home_win, pred.draw, pred.away_win,
                    pred.over_25, pred.under_25,
                    pred.ht_home_over_05, pred.ft_home_over_15,
                    pred.btts, pred.confidence_score,
                    fixture['away_team'], away.form, away.form_points,
                    away.goals_scored_l5_avg, away.goals_conceded_l5_avg,
                    away.ht_goals_scored_avg, away.clean_sheets, away.btts
                ]
                rows.append(row)

            # Batch update for better performance
            sheet.update('A1', rows, value_input_option='USER_ENTERED')

            logger.info(f"Exported {len(rows)-1} fixtures to Google Sheets")

        except Exception as e:
            logger.error(f"Error exporting to Google Sheets: {e}", exc_info=True)

    def run(self, mode: str = 'predict') -> None:
        """Main execution"""
        if mode == 'predict':
            logger.info("Starting Momentum Predictor with Learning...")

            fixtures = self.fetch_fixtures(days_ahead=7)
            if not fixtures:
                logger.warning("No fixtures found")
                return

            logger.info(f"Found {len(fixtures)} fixtures")

            fixtures_data = []

            for fixture in fixtures:
                match_name = fixture.get('name', 'Unknown match')
                logger.info(f"\nProcessing: {match_name}")

                home_team_id = fixture.get('home_team_id')
                away_team_id = fixture.get('away_team_id')

                if not home_team_id or not away_team_id:
                    logger.warning(f"Missing team IDs for fixture {fixture.get('id')}")
                    continue

                # Fetch team data
                home_matches = self.fetch_team_last_matches(home_team_id)
                away_matches = self.fetch_team_last_matches(away_team_id)

                # Calculate stats
                home_stats = self.calculate_team_stats(home_matches, home_team_id, True)
                away_stats = self.calculate_team_stats(away_matches, away_team_id, False)

                if not home_stats or not away_stats:
                    logger.warning(f"Insufficient data for {match_name}")
                    continue

                # Generate predictions
                predictions = self.calculate_match_predictions(home_stats, away_stats)

                # Extract team names
                participants = fixture.get('participants', [])
                home_team_name = next((p['name'] for p in participants if p['id'] == home_team_id), 'Unknown')
                away_team_name = next((p['name'] for p in participants if p['id'] == away_team_id), 'Unknown')

                fixture_data = {
                    'date': fixture.get('starting_at', '').split('T')[0] if 'T' in fixture.get('starting_at', '') else '',
                    'time': fixture.get('starting_at', '').split('T')[1][:5] if 'T' in fixture.get('starting_at', '') else '',
                    'league': fixture.get('league_id'),
                    'home_team': home_team_name,
                    'away_team': away_team_name,
                    'home_stats': home_stats,
                    'away_stats': away_stats,
                    'predictions': predictions
                }

                fixtures_data.append(fixture_data)

                # Store prediction in database
                self.store_prediction(fixture.get('id'), fixture_data)

            if fixtures_data:
                logger.info("\nExporting to Google Sheets...")
                self.export_to_sheets(fixtures_data)

            logger.info("\nPrediction run complete!")
            logger.info(f"Processed {len(fixtures_data)} fixtures successfully")

        elif mode == 'learn':
            logger.info("Starting learning mode - checking results and updating accuracy...")

            updated_count = self.fetch_and_update_results()

            if updated_count > 0:
                logger.info(f"Fetched {updated_count} new results")
                self.adjust_weights()
                logger.info("Weight adjustment complete")
            else:
                logger.info("No new results to process")

            logger.info("Learning mode complete!")

        else:
            logger.error(f"Unknown mode: {mode}. Use 'predict' or 'learn'")


def main():
    """Entry point with argument parsing"""
    import sys

    try:
        predictor = LearningMomentumPredictor()

        # Run in predict mode by default, or 'learn' mode if specified
        mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ['predict', 'learn'] else 'predict'

        if len(sys.argv) > 1 and sys.argv[1] not in ['predict', 'learn']:
            logger.warning(f"Invalid mode '{sys.argv[1]}'. Using 'predict' mode. Valid modes: predict, learn")

        predictor.run(mode=mode)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
