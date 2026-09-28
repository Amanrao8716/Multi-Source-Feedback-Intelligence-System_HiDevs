from io import BytesIO

import pandas as pd
import pytest

from src.ingestion.app_store import fetch_reviews as fetch_apple_reviews
from src.ingestion.csv_importer import import_csv
from src.ingestion.google_play import fetch_reviews as fetch_google_reviews


def test_csv_alias_mapping_and_defaults():
    uploaded = BytesIO(b"Comment,Stars,Date\nGreat work,5,2026-09-01\n")
    result = import_csv(uploaded)
    assert result.iloc[0].review_text == "Great work"
    assert result.iloc[0].source == "CSV Survey"
    assert result.iloc[0].rating == 5


def test_csv_requires_feedback_column():
    with pytest.raises(ValueError, match="feedback"):
        import_csv(BytesIO(b"rating,date\n5,2026-09-01\n"))


def test_csv_supports_explicit_column_mapping():
    uploaded = BytesIO(b"customer_voice,stars_given,submitted\nLogin is broken,1,2026-09-01\n")
    result = import_csv(uploaded, {
        "review_text": "customer_voice", "rating": "stars_given", "review_date": "submitted",
    })
    assert result.iloc[0].review_text == "Login is broken"
    assert result.iloc[0].rating == 1


def test_connectors_validate_identifiers_before_network():
    with pytest.raises(ValueError):
        fetch_google_reviews("invalid", 10)
    with pytest.raises(ValueError):
        fetch_apple_reviews("not-an-id")