-- Supabase Database Schema for Learning Momentum Predictor
-- Run this script in your Supabase SQL Editor

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table to store all predictions
CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    fixture_id BIGINT NOT NULL,
    match_date DATE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    league_id INTEGER NOT NULL,

    -- Predicted percentages
    predicted_home_win_pct INTEGER,
    predicted_draw_pct INTEGER,
    predicted_away_win_pct INTEGER,
    predicted_over_25_pct INTEGER,
    predicted_under_25_pct INTEGER,
    predicted_btts_pct INTEGER,
    predicted_ht_home_over_05_pct INTEGER,
    predicted_ht_away_over_05_pct INTEGER,
    predicted_ft_home_over_15_pct INTEGER,
    predicted_ft_away_over_15_pct INTEGER,

    -- Actual results (null until match finishes)
    actual_result TEXT, -- 'home_win', 'draw', 'away_win'
    actual_home_score INTEGER,
    actual_away_score INTEGER,
    actual_ht_home_score INTEGER,
    actual_ht_away_score INTEGER,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes for faster queries
    CONSTRAINT unique_fixture UNIQUE(fixture_id)
);

-- Indexes for predictions table
CREATE INDEX IF NOT EXISTS idx_predictions_match_date ON predictions(match_date);
CREATE INDEX IF NOT EXISTS idx_predictions_league ON predictions(league_id);
CREATE INDEX IF NOT EXISTS idx_predictions_pending ON predictions(actual_result) WHERE actual_result IS NULL;
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at);

-- Table to track accuracy by prediction type and confidence level
CREATE TABLE IF NOT EXISTS prediction_accuracy (
    id BIGSERIAL PRIMARY KEY,
    prediction_type TEXT NOT NULL, -- 'home_win', 'draw', 'away_win', 'over_25', 'under_25', 'btts', etc
    league_id INTEGER NOT NULL,
    confidence_bucket TEXT NOT NULL, -- '0-30%', '30-50%', '50-70%', '70-100%'

    predictions_made INTEGER DEFAULT 0,
    predictions_correct INTEGER DEFAULT 0,
    accuracy_rate DECIMAL(5,2) DEFAULT 0,

    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_accuracy_record UNIQUE(prediction_type, league_id, confidence_bucket)
);

-- Indexes for prediction_accuracy table
CREATE INDEX IF NOT EXISTS idx_accuracy_type ON prediction_accuracy(prediction_type);
CREATE INDEX IF NOT EXISTS idx_accuracy_league ON prediction_accuracy(league_id);
CREATE INDEX IF NOT EXISTS idx_accuracy_rate ON prediction_accuracy(accuracy_rate DESC);

-- Table to store learning weights for prediction factors
CREATE TABLE IF NOT EXISTS learning_weights (
    id BIGSERIAL PRIMARY KEY,
    factor_name TEXT NOT NULL, -- 'form_points', 'goals_scored_weight', etc
    current_weight DECIMAL(5,3) DEFAULT 1.0,
    prediction_type TEXT NOT NULL, -- 'general', 'home_win', 'over_25', etc

    performance_score DECIMAL(5,3) DEFAULT 0.5, -- How well this factor is performing
    adjustment_count INTEGER DEFAULT 0,

    last_adjusted TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_weight UNIQUE(factor_name, prediction_type)
);

-- Indexes for learning_weights table
CREATE INDEX IF NOT EXISTS idx_weights_factor ON learning_weights(factor_name);
CREATE INDEX IF NOT EXISTS idx_weights_last_adjusted ON learning_weights(last_adjusted DESC);

-- View for quick accuracy overview
CREATE OR REPLACE VIEW accuracy_overview AS
SELECT
    prediction_type,
    league_id,
    SUM(predictions_made) as total_predictions,
    SUM(predictions_correct) as total_correct,
    ROUND(
        (SUM(predictions_correct)::DECIMAL / NULLIF(SUM(predictions_made), 0)) * 100,
        2
    ) as overall_accuracy_pct
FROM prediction_accuracy
GROUP BY prediction_type, league_id
ORDER BY prediction_type, league_id;

-- View for recent prediction performance
CREATE OR REPLACE VIEW recent_performance AS
SELECT
    match_date,
    home_team,
    away_team,
    predicted_home_win_pct,
    predicted_draw_pct,
    predicted_away_win_pct,
    predicted_over_25_pct,
    predicted_btts_pct,
    actual_result,
    actual_home_score,
    actual_away_score,
    CASE
        WHEN actual_result = 'home_win' AND predicted_home_win_pct >= 50 THEN 'Correct'
        WHEN actual_result = 'away_win' AND predicted_away_win_pct >= 50 THEN 'Correct'
        WHEN actual_result = 'draw' AND predicted_draw_pct >= 50 THEN 'Correct'
        WHEN actual_result IS NULL THEN 'Pending'
        ELSE 'Incorrect'
    END as result_prediction_accuracy,
    CASE
        WHEN (actual_home_score + actual_away_score) > 2.5 AND predicted_over_25_pct >= 50 THEN 'Correct'
        WHEN (actual_home_score + actual_away_score) <= 2.5 AND predicted_under_25_pct >= 50 THEN 'Correct'
        WHEN actual_result IS NULL THEN 'Pending'
        ELSE 'Incorrect'
    END as goals_prediction_accuracy,
    created_at
FROM predictions
WHERE actual_result IS NOT NULL
ORDER BY match_date DESC
LIMIT 50;

-- Function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for predictions table
DROP TRIGGER IF EXISTS update_predictions_updated_at ON predictions;
CREATE TRIGGER update_predictions_updated_at
    BEFORE UPDATE ON predictions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default weights
INSERT INTO learning_weights (factor_name, current_weight, prediction_type, performance_score) VALUES
    ('form_points', 1.0, 'general', 0.5),
    ('goals_scored_weight', 1.0, 'general', 0.5),
    ('goals_conceded_weight', 1.0, 'general', 0.5),
    ('home_advantage', 1.0, 'general', 0.5),
    ('ht_goals_weight', 1.0, 'general', 0.5),
    ('trend_multiplier', 1.0, 'general', 0.5),
    ('recent_form_boost', 1.2, 'general', 0.5),
    ('home_away_split', 1.1, 'general', 0.5)
ON CONFLICT (factor_name, prediction_type) DO NOTHING;

-- Useful query examples (commented out, copy to use)

-- Check overall accuracy by prediction type
-- SELECT * FROM accuracy_overview;

-- See recent predictions and their accuracy
-- SELECT * FROM recent_performance;

-- Check which confidence buckets are most accurate
-- SELECT
--     prediction_type,
--     confidence_bucket,
--     predictions_made,
--     accuracy_rate
-- FROM prediction_accuracy
-- WHERE predictions_made >= 5
-- ORDER BY accuracy_rate DESC;

-- See how weights have changed over time
-- SELECT
--     factor_name,
--     current_weight,
--     performance_score,
--     adjustment_count,
--     last_adjusted
-- FROM learning_weights
-- ORDER BY last_adjusted DESC;

-- Find most confident predictions
-- SELECT
--     match_date,
--     home_team,
--     away_team,
--     predicted_home_win_pct,
--     predicted_over_25_pct,
--     actual_result
-- FROM predictions
-- WHERE predicted_home_win_pct >= 70 OR predicted_over_25_pct >= 70
-- ORDER BY match_date DESC;

-- Calculate overall system accuracy
-- SELECT
--     COUNT(*) as total_predictions,
--     SUM(CASE WHEN result_prediction_accuracy = 'Correct' THEN 1 ELSE 0 END) as correct_results,
--     SUM(CASE WHEN goals_prediction_accuracy = 'Correct' THEN 1 ELSE 0 END) as correct_goals,
--     ROUND(
--         (SUM(CASE WHEN result_prediction_accuracy = 'Correct' THEN 1 ELSE 0 END)::DECIMAL / COUNT(*)) * 100,
--         1
--     ) as result_accuracy_pct,
--     ROUND(
--         (SUM(CASE WHEN goals_prediction_accuracy = 'Correct' THEN 1 ELSE 0 END)::DECIMAL / COUNT(*)) * 100,
--         1
--     ) as goals_accuracy_pct
-- FROM recent_performance;

-- Grant permissions (adjust as needed for your Supabase setup)
-- GRANT ALL ON predictions TO authenticated;
-- GRANT ALL ON prediction_accuracy TO authenticated;
-- GRANT ALL ON learning_weights TO authenticated;
-- GRANT SELECT ON accuracy_overview TO authenticated;
-- GRANT SELECT ON recent_performance TO authenticated;

COMMENT ON TABLE predictions IS 'Stores all match predictions with actual results';
COMMENT ON TABLE prediction_accuracy IS 'Tracks prediction accuracy by type and confidence level';
COMMENT ON TABLE learning_weights IS 'Stores learned weights for prediction factors';
COMMENT ON VIEW accuracy_overview IS 'Quick overview of accuracy by prediction type';
COMMENT ON VIEW recent_performance IS 'Recent predictions with accuracy assessment';
