"""
RBI Master Directions scraper.

The Master Directions hub page (https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx)
is plain server-rendered HTML. Each entry looks roughly like:

    <a href="/Scripts/BS_ViewMasDirections.aspx?id=13141">
        Reserve Bank of India (Commercial Banks – Know Your Customer) Directions, 2025
        (Updated as on December 29, 2025)
    </a>
    <a href="https://rbidocs.rbi.org.in/rdocs/notification/PDFs/169MD.PDF">
        PDF - ... 683 kb
    </a>

Section headers (category names like "Commercial Banks", "Know Your Customer")
appear as bold/heading text interspersed between links, not as clean HTML
containers — so we track "current category" as we walk through the page,
rather than trying to select a table row.

IMPORTANT: run this once on a live fetch and inspect the actual tag structure
(<strong>, <b>, <p>, or bare text nodes) before trusting the category-tracking
logic below — RBI's markup is inconsistent across sections. Treat this as a
first draft to adjust against real output.
"""

import json
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ComplianceIngestBot/1.0; contact=you@yourcompany.com)"
}
MASTER_DIRECTIONS_URL = "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx"

# Keywords to filter for your three topics. Match against the *direction title*.
TOPIC_KEYWORDS = {
    "kyc": ["know your customer"],
    "loans": [
        "credit facilities",
        "credit cards",
        "interest rates on advances",
        "recovery of loans",
    ],
    "consumer_protection": ["internal ombudsman", "consumer education"],
}


def matches_topic(title: str) -> list[str]:
    title_lower = title.lower()
    matched = []
    for topic, kws in TOPIC_KEYWORDS.items():
        if any(kw in title_lower for kw in kws):
            matched.append(topic)
    return matched


def fetch_master_directions_list(url: str = MASTER_DIRECTIONS_URL) -> list[dict]:
    """
    Returns a list of dicts:
    {
        "title": str,
        "detail_page_url": str,       # BS_ViewMasDirections.aspx?id=...
        "pdf_url": str,               # direct PDF link
        "matched_topics": [str],
    }
    Only entries matching TOPIC_KEYWORDS are returned — comment out the
    filter at the bottom if you want everything for manual review first.
    """
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    # Every direction title link points to BS_ViewMasDirections.aspx
    # The PDF link is its immediate sibling <a> pointing to rbidocs.rbi.org.in
    direction_links = soup.find_all(
        "a", href=re.compile(r"BS_ViewMasDirections\.aspx\?id=\d+")
    )

    for link in direction_links:
        title = link.get_text(strip=True)
        detail_url = urljoin(url, link["href"])

        # Look for the next sibling <a> tag that points to a PDF
        pdf_url = None
        sib = link.find_next("a")
        if sib and sib.get("href", "").lower().endswith(".pdf"):
            pdf_url = sib["href"]

        matched = matches_topic(title)
        if (
            matched
        ):  # remove this condition to capture everything for a first manual pass
            results.append(
                {
                    "title": title,
                    "detail_page_url": detail_url,
                    "pdf_url": pdf_url,
                    "matched_topics": matched,
                }
            )

    return results


if __name__ == "__main__":
    docs = fetch_master_directions_list()
    print(f"Found {len(docs)} matching documents\n")
    for d in docs:
        print(f"[{', '.join(d['matched_topics'])}] {d['title']}")
        print(f"   PDF: {d['pdf_url']}\n")

    with open("matched_directions.json", "w") as f:
        json.dump(docs, f, indent=2)
    print("Saved to matched_directions.json")
