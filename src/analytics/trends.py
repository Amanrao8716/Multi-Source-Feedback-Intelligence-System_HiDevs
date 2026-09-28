"""Compare negative issue frequency across adjacent periods."""

from __future__ import annotations

import pandas as pd


def compare_issue_trends(data: pd.DataFrame, period_days: int = 30, minimum_previous: int = 2) -> pd.DataFrame:
    columns = ["category", "current_negative", "previous_negative", "change", "change_pct", "trend"]
    if data.empty or not {"category", "sentiment", "review_date"}.issubset(data.columns):
        return pd.DataFrame(columns=columns)

    frame = data[data.sentiment.eq("negative")].copy()
    frame["review_date"] = pd.to_datetime(frame.review_date, utc=True, errors="coerce")
    frame = frame.dropna(subset=["review_date"])
    if frame.empty:
        return pd.DataFrame(columns=columns)

    end = frame.review_date.max()
    current_start = end - pd.Timedelta(days=period_days)
    previous_start = current_start - pd.Timedelta(days=period_days)
    current = frame[(frame.review_date > current_start) & (frame.review_date <= end)].groupby("category").size()
    previous = frame[(frame.review_date > previous_start) & (frame.review_date <= current_start)].groupby("category").size()
    categories = sorted(set(current.index) | set(previous.index))
    rows = []
    for category in categories:
        current_count = int(current.get(category, 0))
        previous_count = int(previous.get(category, 0))
        change = current_count - previous_count
        change_pct = (change / previous_count * 100) if previous_count else None
        if previous_count < minimum_previous:
            trend = "New" if current_count and previous_count == 0 else "Insufficient baseline"
        elif change > 0:
            trend = "Increasing"
        elif change < 0:
            trend = "Declining"
        else:
            trend = "Stable"
        rows.append({"category": category, "current_negative": current_count,
                     "previous_negative": previous_count, "change": change,
                     "change_pct": change_pct, "trend": trend})
    return pd.DataFrame(rows, columns=columns).sort_values("change", ascending=False).reset_index(drop=True)