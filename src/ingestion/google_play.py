"""Google Play review connector backed by google-play-scraper."""

from __future__ import annotations

import pandas as pd


def fetch_reviews(package_name: str, limit: int = 100) -> pd.DataFrame:
    if not package_name or "." not in package_name.strip() or limit < 1:
        raise ValueError("Enter a valid Google Play package name and a positive review limit.")
    try:
        from google_play_scraper import Sort, reviews
    except ImportError as error:
        raise RuntimeError("Google Play support is unavailable. Install google-play-scraper.") from error
    try:
        records, _ = reviews(package_name.strip(), lang="en", country="us", sort=Sort.NEWEST, count=min(limit, 2000))
    except Exception as error:
        raise RuntimeError(f"Google Play could not retrieve reviews: {error}") from error
    rows = [{"source": "Google Play", "review_text": item.get("content"),
             "rating": item.get("score"), "review_date": item.get("at"),
             "author": item.get("userName")} for item in records]
    return pd.DataFrame(rows, columns=["source", "review_text", "rating", "review_date", "author"])