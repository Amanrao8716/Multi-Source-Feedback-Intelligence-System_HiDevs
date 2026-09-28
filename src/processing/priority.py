"""Explainable issue-level prioritization; single reviews cannot become critical."""

from __future__ import annotations

import pandas as pd


def prioritize_issues(data: pd.DataFrame) -> pd.DataFrame:
    columns = ["category", "total_feedback", "negative_count", "negative_pct", "average_rating", "recent_negative", "priority_score", "priority_level", "factors"]
    if data.empty or "category" not in data:
        return pd.DataFrame(columns=columns)

    frame = data.copy()
    frame["review_date"] = pd.to_datetime(frame["review_date"], utc=True, errors="coerce")
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=30)
    rows = []
    for category, group in frame.groupby("category", dropna=False):
        negative = group[group.sentiment.eq("negative")]
        negative_count = len(negative)
        negative_pct = 100 * negative_count / max(len(group), 1)
        average_rating = group.rating.mean()
        recent_count = int((negative.review_date >= cutoff).sum())
        severity = negative.review_text.astype(str).str.contains(
            r"(?:can't use|cannot use|data loss|security|keeps crashing|completely broken)",
            case=False, regex=True
        ).sum()
        score = min(100.0, negative_count * 8 + negative_pct * 0.25 + (5 - average_rating) * 5 if pd.notna(average_rating) else negative_count * 8 + negative_pct * 0.25)
        score = min(100.0, score + min(int(severity) * 8, 24) + min(recent_count, 5) * 2)
        if negative_count >= 5 and score >= 70:
            level = "Critical"
        elif negative_count >= 3 and score >= 45:
            level = "High"
        elif negative_count >= 2 and score >= 25:
            level = "Medium"
        else:
            level = "Low"
        rating_factor = f"{average_rating:.1f}/5 average rating" if pd.notna(average_rating) else "rating unavailable"
        factors = (f"{negative_count} negative reviews; {negative_pct:.0f}% negative; {rating_factor}; "
               f"{int(severity)} severity indicator(s); {recent_count} negative in last 30 days")
        rows.append({"category": category, "total_feedback": len(group), "negative_count": negative_count,
                     "negative_pct": negative_pct, "average_rating": average_rating,
                     "recent_negative": recent_count, "priority_score": round(score, 1),
                     "priority_level": level, "factors": factors})
    return pd.DataFrame(rows, columns=columns).sort_values("priority_score", ascending=False).reset_index(drop=True)