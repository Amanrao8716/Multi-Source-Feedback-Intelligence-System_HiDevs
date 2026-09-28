"""Apple App Store customer reviews from Apple's public RSS endpoint."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pandas as pd
import requests

RSS_URL = "https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/xml"


def fetch_reviews(app_id: str, country: str = "us", timeout: int = 15) -> pd.DataFrame:
    if not str(app_id).strip().isdigit():
        raise ValueError("Apple App Store app ID must contain digits only.")
    url = RSS_URL.format(country=country.lower(), app_id=app_id.strip())
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "FeedbackIntelligence/1.0"})
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except (requests.RequestException, ET.ParseError) as error:
        raise RuntimeError(f"Apple App Store reviews are unavailable: {error}") from error

    rows = []
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        rating = entry.find("{http://itunes.apple.com/rss}rating")
        content = entry.find("{http://www.w3.org/2005/Atom}content")
        updated = entry.find("{http://www.w3.org/2005/Atom}updated")
        author = entry.find("{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name")
        if content is None or content.text is None:
            continue
        rows.append({"source": "Apple App Store", "review_text": content.text,
                     "rating": rating.text if rating is not None else None,
                     "review_date": updated.text if updated is not None else None,
                     "author": author.text if author is not None else None})
    return pd.DataFrame(rows, columns=["source", "review_text", "rating", "review_date", "author"])