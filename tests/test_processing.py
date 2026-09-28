import pandas as pd

from src.ingestion.aggregator import process_feedback
from src.processing.cleaner import clean_feedback
from src.processing.sentiment import SentimentEngine


def test_cleaning_reports_invalid_rows_and_duplicates():
    rows = pd.DataFrame([
        {"source": "google play", "review_text": "  Great app  ", "rating": 5, "review_date": "2026-09-01"},
        {"source": "Google Play", "review_text": "Great app", "rating": 5, "review_date": "2026-09-01"},
        {"source": "CSV", "review_text": "", "rating": 9, "review_date": "bad-date"},
    ])
    result = clean_feedback(rows)
    assert result.accepted == 1
    assert result.duplicates == 1
    assert result.rejected == 1
    assert result.modified == 1
    assert result.data.iloc[0].source == "Google Play"


def test_sentiment_handles_empty_and_polar_text():
    engine = SentimentEngine()
    assert engine.analyze_text("")["sentiment"] == "neutral"
    assert engine.analyze_text("This is excellent and works perfectly") ["sentiment"] == "positive"
    assert engine.analyze_text("It crashes constantly and is terrible") ["sentiment"] == "negative"


def test_pipeline_adds_sentiment_category_and_priority():
    source = pd.DataFrame([{
        "source": "CSV", "review_text": "The app crashes every time", "rating": 1,
        "review_date": "2026-09-01",
    }])
    result, details = process_feedback(source)
    assert result.iloc[0].sentiment == "negative"
    assert result.iloc[0].category == "Bugs and Errors"
    assert result.iloc[0].priority_level == "Low"
    assert details["accepted"] == 1


def test_cleaner_accepts_empty_frame():
    result = clean_feedback(pd.DataFrame())
    assert result.data.empty
    assert result.accepted == 0