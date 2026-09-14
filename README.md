# The Polite Scraper

Backend AI Engineering — Week 5 — BE-05

## Target Classification

This project scrapes Books to Scrape, a public practice sandbox
designed for learning web scraping.

Target:
https://books.toscrape.com/

Scope:
Only the first 3 catalogue pages will be processed.

Expected data:
- title
- product URL
- price
- availability
- rating
- description
- source page
- fetched timestamp

## Robots Check

The scraper checks:

https://books.toscrape.com/robots.txt

The result of this check will be documented here after running
the scraper.

## Politeness

The scraper:
- identifies itself with a User-Agent
- uses a request timeout
- waits at least 500 ms between real requests
- caches downloaded pages
- checks HTTP status codes
- does not repeatedly request failed pages

I will not reuse this code on another site without checking its rules and terms first.