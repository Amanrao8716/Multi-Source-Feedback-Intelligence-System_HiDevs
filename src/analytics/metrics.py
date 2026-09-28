"""Descriptive metrics for the feedback dashboard and reports."""

from __future__ import annotations

import pandas as pd


def sentiment_summary(data: pd.DataFrame) -> dict[str, object]:
    total = len(data)
    counts = data.sentiment.value_counts() if total and "sentiment" in data else pd.Series(dtype=int)
    return {"total": total,
            "positive_pct": 100 * counts.get("positive", 0) / total if total else 0.0,
            "negative_pct": 100 * counts.get("negative", 0) / total if total else 0.0,
            "neutral_pct": 100 * counts.get("neutral", 0) / total if total else 0.0,
            "average_rating": data.rating.mean() if total and "rating" in data else None,
            "sources": int(data.source.nunique()) if total and "source" in data else 0,
            "sentiment_counts": counts.to_dict()}


def volume_over_time(data: pd.DataFrame, frequency: str = "W") -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame(columns=["period", "feedback_count", "average_rating"])
    frame = data.copy()
    frame["review_date"] = pd.to_datetime(frame.review_date, utc=True, errors="coerce")
    frame = frame.dropna(subset=["review_date"]).set_index("review_date")
    grouped = frame.resample(frequency).agg(feedback_count=("feedback_id", "count"), average_rating=("rating", "mean"))
    grouped.index = grouped.index.tz_localize(None)
    return grouped.reset_index(names="period")


def period_comparison(data: pd.DataFrame, end_date=None, days: int = 7) -> dict[str, object]:
    if data.empty:
        return {"current_count": 0, "previous_count": 0, "change_pct": None}
    dates = pd.to_datetime(data.review_date, utc=True, errors="coerce")
    end = pd.Timestamp(end_date or dates.max()).tz_localize("UTC") if pd.Timestamp(end_date or dates.max()).tzinfo is None else pd.Timestamp(end_date or dates.max()).tz_convert("UTC")
    current_start = end - pd.Timedelta(days=days)
    previous_start = current_start - pd.Timedelta(days=days)
    current = int(((dates > current_start) & (dates <= end)).sum())
    previous = int(((dates > previous_start) & (dates <= current_start)).sum())
    change = ((current - previous) / previous * 100) if previous else None
    return {"current_count": current, "previous_count": previous, "change_pct": change}