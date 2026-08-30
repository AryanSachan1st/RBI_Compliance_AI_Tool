import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ComplianceBot/1.0)"}


def fetch_listing_page(url: str) -> list[dict]:
    """Returns list of {title, url, date_str} for each document link found."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    # NOTE: selector below is illustrative — inspect actual page HTML
    # and adjust to the real table/list structure before running
    for row in soup.select("table tr"):  # placeholder selector
        link_tag = row.find("a", href=True)
        if not link_tag:
            continue
        results.append(
            {
                "title": link_tag.get_text(strip=True),
                "url": urljoin(url, link_tag["href"]),
                "date_str": row.get_text(
                    " ", strip=True
                ),  # parse date out of this later
            }
        )
        time.sleep(0.5)  # be polite, avoid hammering the server
    return results


fetch_listing_page("https://rbidocs.rbi.org.in/rdocs/notification/PDFs/169MD.PDF")
