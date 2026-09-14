# FlyRank BE-05 — The Polite Scraper

A small Python web scraper built for the FlyRank Backend AI Engineering internship assignment **BE-05: The Polite Scraper**.

The scraper collects book data from [Books to Scrape](https://books.toscrape.com/), extracts structured information, normalizes prices, validates records with Pydantic, handles failed pages safely, and stores the results as JSON.

## Features

* Collects books from the first 3 catalogue pages
* Targets 60 unique books
* Uses `BeautifulSoup` for HTML parsing
* Converts price text such as `£51.77` into a numeric `price_gbp` value
* Extracts:

  * Title
  * Product URL
  * Price
  * Availability
  * Rating
  * Description
  * Source catalogue page
  * Fetch timestamp
* Validates records using a Pydantic schema
* Uses a descriptive User-Agent
* Checks `robots.txt` before scraping
* Adds a polite delay between requests
* Uses local caching to avoid unnecessary repeated requests
* Retries temporary network failures
* Handles HTTP failures without crashing the complete pipeline
* Generates a run report with scraping statistics

## Project Structure

```text
polite-scraper/
│
├── src/
│   └── main.py
│
├── output/
│   ├── books.json
│   ├── errors.json
│   └── run-report.json
│
├── cache/
│   └── downloaded HTML pages
│
├── requirements.txt
├── README.md
└── .gitignore
```

The `cache/` directory is used locally and should normally be excluded from Git with `.gitignore`.

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/polite-scraper.git
cd polite-scraper
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

Run the scraper with:

```bash
python src/main.py
```

The scraper checks the site's `robots.txt`, discovers books from three catalogue pages, fetches the book detail pages, validates the extracted records, and generates JSON output files.

## Output Files

### `output/books.json`

Contains successfully validated book records.

Example structure:

```json
{
  "title": "Example Book",
  "product_url": "https://books.toscrape.com/",
  "price_text": "£20.00",
  "price_gbp": 20.0,
  "availability_text": "In stock",
  "rating_text": "Three",
  "description": "Book description",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-01-01T00:00:00+00:00"
}
```

### `output/errors.json`

Stores records that fail schema validation.

### `output/run-report.json`

Contains execution statistics such as:

* Start time
* Duration
* Pages fetched
* Cache hits
* Valid records
* Invalid records
* Failed pages

## Polite Scraping Practices

The scraper is designed to minimize unnecessary load on the target website.

It:

1. Checks `robots.txt`
2. Identifies itself using a User-Agent
3. Waits between requests
4. Caches downloaded pages
5. Uses limited retries for network failures
6. Does not continuously retry client errors such as `404` or `403`
7. Continues processing when an individual page fails

## Validation

Each extracted record is validated using the `RawBookRecord` Pydantic model.

Important fields include:

```text
title
product_url
price_text
price_gbp
availability_text
rating_text
description
source_page
fetched_at
```

## Error Handling

A failed page does not terminate the complete scraping pipeline.

Network failures and HTTP errors are recorded by the run tracker, while schema validation failures are written to `errors.json`.

## Assignment

**FlyRank Backend AI Engineering**

**Assignment:** BE-05 — The Polite Scraper

**Source:** Books to Scrape

The project demonstrates polite web scraping, HTML parsing, data normalization, schema validation, caching, retry handling, and structured JSON output.
