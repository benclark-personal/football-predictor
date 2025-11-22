"""
Daily Predictions Runner
Fetches predictions for today + next 2 days across all leagues
Designed for daily automation (cron/scheduled task)
"""

import os
import sys
import time
import logging
from datetime import datetime
from main_footballdata import FootballDataPredictor, COMPETITIONS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_predictor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Run daily predictions for all leagues (today + next 2 days)"""

    start_time = datetime.now()
    logger.info("")
    logger.info("="*80)
    logger.info("DAILY PREDICTION RUN - ALL LEAGUES")
    logger.info("="*80)
    logger.info(f"Run time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Looking ahead: 3 days (today + next 2 days)")
    logger.info(f"Total leagues: {len(COMPETITIONS)}")
    logger.info(f"Leagues: {', '.join(COMPETITIONS.keys())}")
    logger.info("="*80)
    logger.info("")

    try:
        # Initialize predictor
        predictor = FootballDataPredictor()

        total_predictions = 0
        league_stats = {}

        # Process each league
        for i, (competition_code, competition_id) in enumerate(COMPETITIONS.items()):
            logger.info("")
            logger.info("="*80)
            logger.info(f"League {i+1}/{len(COMPETITIONS)}: {competition_code}")
            logger.info("="*80)

            try:
                # Modify predictor to use 3 days ahead
                # We'll fetch fixtures for 3 days (today + next 2)
                fixtures = predictor.fetch_upcoming_fixtures(competition_code, days_ahead=3)

                if not fixtures:
                    logger.info(f"No upcoming fixtures found for {competition_code}")
                    league_stats[competition_code] = 0

                    # Still wait between leagues to respect rate limits
                    if i < len(COMPETITIONS) - 1:
                        logger.info(f"Pausing 60 seconds before next league...")
                        time.sleep(60)
                    continue

                logger.info(f"Found {len(fixtures)} upcoming fixtures")
                predictions_made = 0

                for fixture in fixtures:
                    home_team = fixture['homeTeam']
                    away_team = fixture['awayTeam']
                    match_date = datetime.fromisoformat(fixture['utcDate'].replace('Z', '+00:00'))

                    logger.info(f"\n{home_team['shortName']} vs {away_team['shortName']}")
                    logger.info(f"Date: {match_date.strftime('%Y-%m-%d %H:%M UTC')}")

                    # Fetch team histories
                    home_matches = predictor.fetch_team_matches(home_team['id'])
                    away_matches = predictor.fetch_team_matches(away_team['id'])

                    if not home_matches or not away_matches:
                        logger.warning("Insufficient match data, skipping")
                        continue

                    # Calculate stats
                    home_stats = predictor.calculate_team_stats(home_matches, home_team['id'])
                    away_stats = predictor.calculate_team_stats(away_matches, away_team['id'])

                    if not home_stats or not away_stats:
                        logger.warning("Could not calculate stats, skipping")
                        continue

                    # Generate predictions
                    predictions = predictor.calculate_predictions(home_stats, away_stats)

                    # Display predictions
                    logger.info(f"Form: {home_stats.form} vs {away_stats.form}")
                    logger.info(f"Result: Home {predictions.home_win}% | Draw {predictions.draw}% | Away {predictions.away_win}%")
                    logger.info(f"Goals: O0.5 {predictions.over_05}% | O1.5 {predictions.over_15}% | O2.5 {predictions.over_25}% | O3.5 {predictions.over_35}%")
                    logger.info(f"BTTS: {predictions.btts}% | Confidence: {predictions.confidence_score}")

                    # Store in database
                    predictor.store_prediction(fixture, predictions)
                    predictions_made += 1

                league_stats[competition_code] = predictions_made
                total_predictions += predictions_made

                logger.info("")
                logger.info(f"Completed {competition_code}: {predictions_made} predictions made")

            except Exception as e:
                logger.error(f"Error processing {competition_code}: {e}")
                league_stats[competition_code] = 0

            # Rate limiting: Wait 60 seconds between leagues (except after last one)
            if i < len(COMPETITIONS) - 1:
                logger.info("")
                logger.info(f"Rate limit pause: 60 seconds...")
                logger.info("")
                time.sleep(60)

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("")
        logger.info("="*80)
        logger.info("DAILY PREDICTION RUN COMPLETED")
        logger.info("="*80)
        logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Duration: {int(duration // 60)} minutes {int(duration % 60)} seconds")
        logger.info(f"Total predictions: {total_predictions}")
        logger.info("")
        logger.info("League breakdown:")

        for league, count in league_stats.items():
            logger.info(f"  {league}: {count} predictions")

        logger.info("="*80)
        logger.info("")

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
