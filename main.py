import json
import os
import re
import time

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError


# ============================================================
# Configuration Constants
# ============================================================

BASE_URL = "https://books.toscrape.com/"

ROBOTS_URL = urljoin(BASE_URL, "robots.txt")

USER_AGENT = (
    "FlyRankInternshipA9/1.0 "
    "(+https://github.com/your-username/polite-scraper)"
)

POLITE_DELAY_SEC = 0.5
TIMEOUT_SEC = 10.0

CACHE_DIR = Path("cache")
OUTPUT_DIR = Path("output")

CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# Stage 4: Pydantic Schema
# ============================================================

class RawBookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: HttpUrl
    fetched_at: str


# ============================================================
# Run Tracker
# ============================================================

class RunTracker:

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.pages_fetched = 0
        self.cache_hits = 0
        self.valid_records = 0
        self.invalid_records = 0
        self.failed_pages = []

    def export(self):
        end_time = datetime.now(timezone.utc)

        duration = (
            end_time - self.start_time
        ).total_seconds()

        return {
            "start_time": self.start_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "pages_fetched": self.pages_fetched,
            "cache_hits": self.cache_hits,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "failed_pages_count": len(self.failed_pages),
            "failed_pages": self.failed_pages,
        }


tracker = RunTracker()


# ============================================================
# Stage 1: Check robots.txt
# ============================================================

def check_robots():
    """
    Check the website's robots.txt before scraping.
    """

    print("\nChecking robots.txt...")

    headers = {
        "User-Agent": USER_AGENT
    }

    try:
        response = requests.get(
            ROBOTS_URL,
            headers=headers,
            timeout=TIMEOUT_SEC
        )

        print(f"robots.txt status: {response.status_code}")

        if response.status_code == 200:
            print("robots.txt found and checked.")

            # Show a small preview for logging
            preview = response.text[:500]

            if preview.strip():
                print("robots.txt preview:")
                print(preview)
            else:
                print("robots.txt is empty.")

        elif response.status_code == 404:
            print(
                "robots.txt is not available (404). "
                "Continuing with polite scraping behavior."
            )

        else:
            print(
                f"robots.txt returned status {response.status_code}. "
                "Continuing carefully."
            )

    except requests.RequestException as e:
        print(f"Could not check robots.txt: {e}")
        print("Continuing with polite scraping behavior.")


# ============================================================
# Stage 1 & 5: Fetch, Cache, and Retry
# ============================================================

def fetch_page(url: str, cache_key: str) -> Optional[str]:

    cache_path = CACHE_DIR / f"{cache_key}.html"

    # --------------------------------------------------------
    # Use cached page if available
    # --------------------------------------------------------

    if cache_path.exists():

        tracker.cache_hits += 1

        print(f"[CACHE] {url}")

        try:
            return cache_path.read_text(
                encoding="utf-8"
            )
        except Exception as e:
            print(f"Cache read failed: {e}")

    # --------------------------------------------------------
    # Request headers
    # --------------------------------------------------------

    headers = {
        "User-Agent": USER_AGENT
    }

    # --------------------------------------------------------
    # Two attempts maximum
    # --------------------------------------------------------

    for attempt in range(2):

        try:

            # Polite delay before request
            time.sleep(POLITE_DELAY_SEC)

            print(
                f"[FETCH] Attempt {attempt + 1}/2: {url}"
            )

            response = requests.get(
                url,
                headers=headers,
                timeout=TIMEOUT_SEC
            )

            # ------------------------------------------------
            # Successful request
            # ------------------------------------------------

            if response.status_code == 200:

                tracker.pages_fetched += 1

                cache_path.write_text(
                    response.text,
                    encoding="utf-8"
                )

                return response.text

            # ------------------------------------------------
            # Client errors: don't retry
            # ------------------------------------------------

            elif response.status_code in (404, 403):

                tracker.failed_pages.append(
                    {
                        "url": url,
                        "status": response.status_code
                    }
                )

                print(
                    f"[FAILED] HTTP {response.status_code}: {url}"
                )

                return None

            # ------------------------------------------------
            # Other HTTP errors
            # ------------------------------------------------

            else:

                print(
                    f"[FAILED] HTTP {response.status_code}: {url}"
                )

                if attempt == 1:

                    tracker.failed_pages.append(
                        {
                            "url": url,
                            "status": response.status_code
                        }
                    )

                    return None

        except requests.RequestException as e:

            print(
                f"[NETWORK ERROR] Attempt {attempt + 1}: {e}"
            )

            if attempt == 1:

                tracker.failed_pages.append(
                    {
                        "url": url,
                        "error": "Timeout/Network Failure"
                    }
                )

                return None

            # Pause before retry
            time.sleep(1.0)

    return None


# ============================================================
# Stage 2: Discover Catalogue Pages
# ============================================================

def discover_book_urls() -> list[tuple[str, str]]:

    discovered = []

    current_url = BASE_URL

    page_count = 0

    while current_url and page_count < 3:

        page_count += 1

        print(
            f"\nDiscovering catalogue page {page_count}/3..."
        )

        cache_key = f"catalogue-page-{page_count}"

        html = fetch_page(
            current_url,
            cache_key
        )

        if not html:

            print(
                f"Could not fetch catalogue page {page_count}."
            )

            break

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # Find books
        articles = soup.select(
            "article.product_pod"
        )

        print(
            f"Found {len(articles)} books on page {page_count}."
        )

        for article in articles:

            link = article.select_one(
                "h3 a"
            )

            if link and "href" in link.attrs:

                abs_url = urljoin(
                    current_url,
                    link["href"]
                )

                discovered.append(
                    (
                        abs_url,
                        current_url
                    )
                )

        # Find next page
        next_btn = soup.select_one(
            "li.next a"
        )

        if next_btn and "href" in next_btn.attrs:

            current_url = urljoin(
                current_url,
                next_btn["href"]
            )

        else:

            current_url = None

    # --------------------------------------------------------
    # Deduplicate while preserving order
    # --------------------------------------------------------

    unique_books = []

    seen = set()

    for book_url, source_page in discovered:

        if book_url not in seen:

            seen.add(book_url)

            unique_books.append(
                (
                    book_url,
                    source_page
                )
            )

    print(
        f"\nTotal unique books discovered: {len(unique_books)}"
    )

    return unique_books


# ============================================================
# Stage 3: Extract Raw Book Data
# ============================================================

def parse_book_detail(
    url: str,
    source_page: str,
    idx: int
) -> Optional[dict]:

    cache_key = f"book-detail-{idx}"

    html = fetch_page(
        url,
        cache_key
    )

    if not html:

        return None

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # --------------------------------------------------------
    # Main product section
    # --------------------------------------------------------

    main = soup.select_one(
        "div.product_main"
    )

    if not main:

        tracker.failed_pages.append(
            {
                "url": url,
                "error": "Product section not found"
            }
        )

        return None

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title_el = main.select_one("h1")

    title = (
        title_el.get_text(strip=True)
        if title_el
        else ""
    )

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    price_el = main.select_one(
        "p.price_color"
    )

    price_text = (
        price_el.get_text(strip=True)
        if price_el
        else ""
    )

    # --------------------------------------------------------
    # Availability
    # --------------------------------------------------------

    avail_el = main.select_one(
        "p.instock.availability"
    )

    avail_text = (
        avail_el.get_text(strip=True)
        if avail_el
        else ""
    )

    # --------------------------------------------------------
    # Rating
    # --------------------------------------------------------

    rating_el = main.select_one(
        "p.star-rating"
    )

    rating_text = ""

    if rating_el:

        classes = rating_el.get(
            "class",
            []
        )

        rating_text = next(
            (
                c
                for c in classes
                if c != "star-rating"
            ),
            ""
        )

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    desc_el = soup.select_one(
        "#product_description ~ p"
    )

    description = (
        desc_el.get_text(strip=True)
        if desc_el
        else None
    )

    # ========================================================
    # Stage 4: Normalization
    # ========================================================

    price_match = re.search(
        r"[\d\.]+",
        price_text
    )

    price_gbp = (
        float(price_match.group())
        if price_match
        else 0.0
    )

    # ========================================================
    # Return structured raw data
    # ========================================================

    return {

        "title": title,

        "product_url": url,

        "price_text": price_text,

        "price_gbp": price_gbp,

        "availability_text": avail_text,

        "rating_text": rating_text,

        "description": description,

        "source_page": source_page,

        "fetched_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# ============================================================
# Pipeline Execution
# ============================================================

def main():

    print("=" * 60)
    print("FLYRANK BE-05 - THE POLITE SCRAPER")
    print("=" * 60)

    # --------------------------------------------------------
    # Stage 1: Check robots.txt
    # --------------------------------------------------------

    check_robots()

    # --------------------------------------------------------
    # Stage 2: Discover books
    # --------------------------------------------------------

    book_targets = discover_book_urls()

    print(
        f"\nDiscovered {len(book_targets)} unique books."
    )

    # --------------------------------------------------------
    # Stage 5 Test:
    # Deliberate broken URL
    #
    # Uncomment ONLY when you want to test failure handling.
    # --------------------------------------------------------

    # book_targets.append(
    #     (
    #         "https://books.toscrape.com/"
    #         "catalogue/fake-broken-book_9999/index.html",
    #         BASE_URL
    #     )
    # )

    # --------------------------------------------------------
    # Process books
    # --------------------------------------------------------

    valid_records = []

    error_records = []

    for idx, (url, source_page) in enumerate(
        book_targets,
        start=1
    ):

        print(
            f"\n[{idx}/{len(book_targets)}] Processing book..."
        )

        raw_data = parse_book_detail(
            url,
            source_page,
            idx
        )

        # Failed page
        if not raw_data:

            print(
                "Skipping failed book/page."
            )

            continue

        # ----------------------------------------------------
        # Stage 4: Pydantic Validation
        # ----------------------------------------------------

        try:

            validated = RawBookRecord(
                **raw_data
            )

            valid_records.append(
                validated.model_dump(
                    mode="json"
                )
            )

            tracker.valid_records += 1

            print(
                f"VALID: {validated.title}"
            )

        except ValidationError as e:

            error_records.append(
                {
                    "raw_data": raw_data,
                    "error": e.errors()
                }
            )

            tracker.invalid_records += 1

            print(
                f"INVALID: {url}"
            )

    # ========================================================
    # Output Generation
    # ========================================================

    books_file = OUTPUT_DIR / "books.json"

    errors_file = OUTPUT_DIR / "errors.json"

    report_file = OUTPUT_DIR / "run-report.json"

    # --------------------------------------------------------
    # books.json
    # --------------------------------------------------------

    books_file.write_text(
        json.dumps(
            valid_records,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # errors.json
    # --------------------------------------------------------

    errors_file.write_text(
        json.dumps(
            error_records,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # run-report.json
    # --------------------------------------------------------

    report_file.write_text(
        json.dumps(
            tracker.export(),
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # ========================================================
    # Final Report
    # ========================================================

    print("\n" + "=" * 60)
    print("PIPELINE FINISHED")
    print("=" * 60)

    print(
        f"Books discovered : {len(book_targets)}"
    )

    print(
        f"Valid records    : {len(valid_records)}"
    )

    print(
        f"Invalid records  : {len(error_records)}"
    )

    print(
        f"Failed pages     : {len(tracker.failed_pages)}"
    )

    print(
        f"Cache hits       : {tracker.cache_hits}"
    )

    print(
        f"Pages fetched    : {tracker.pages_fetched}"
    )

    print("\nOutput files:")

    print(
        f" - {books_file}"
    )

    print(
        f" - {errors_file}"
    )

    print(
        f" - {report_file}"
    )

    print("=" * 60)


# ============================================================
# Program Entry Point
# ============================================================

if __name__ == "__main__":
    main()