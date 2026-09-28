import pandas as pd

from src.analytics.metrics import period_comparison, sentiment_summary, volume_over_time
from src.analytics.trends import compare_issue_trends
from src.reporting.pdf_report import generate_pdf


def test_metrics_and_empty_analytics():
    assert sentiment_summary(pd.DataFrame())["total"] == 0
    assert volume_over_time(pd.DataFrame()).empty
    assert period_comparison(pd.DataFrame())["change_pct"] is None
    data = pd.DataFrame({"sentiment": ["positive", "negative"], "rating": [5, 1],
                         "source": ["CSV", "CSV"]})
    assert sentiment_summary(data)["negative_pct"] == 50


def test_issue_trends_compare_adjacent_periods_with_baseline_caveat():
    data = pd.DataFrame([
        {"category": "Bugs", "sentiment": "negative", "review_date": "2026-08-01"},
        {"category": "Bugs", "sentiment": "negative", "review_date": "2026-08-10"},
        {"category": "Bugs", "sentiment": "negative", "review_date": "2026-09-10"},
        {"category": "Bugs", "sentiment": "negative", "review_date": "2026-09-15"},
        {"category": "Bugs", "sentiment": "negative", "review_date": "2026-09-20"},
        {"category": "Login", "sentiment": "negative", "review_date": "2026-09-20"},
    ])
    trends = compare_issue_trends(data)
    bugs = trends[trends.category.eq("Bugs")].iloc[0]
    login = trends[trends.category.eq("Login")].iloc[0]
    assert bugs.trend == "Increasing"
    assert bugs.change == 1
    assert login.trend == "New"


def test_pdf_generation_with_empty_and_populated_data():
    empty = generate_pdf(pd.DataFrame())
    assert empty.startswith(b"%PDF")
    populated = pd.DataFrame([{
        "feedback_id": "1", "source": "CSV Survey", "review_text": "It crashes constantly.",
        "rating": 1.0, "review_date": pd.Timestamp("2026-09-01", tz="UTC"),
        "sentiment": "negative", "sentiment_score": -0.5, "confidence": 0.5,
        "category": "Bugs and Errors", "priority_score": 10, "priority_level": "Low",
        "processed": True,
    }])
    assert generate_pdf(populated).startswith(b"%PDF")