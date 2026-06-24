# Maintenance Log

## 2026-06-24

- Applied a medium project-structure cleanup following the product-style project management guide.
- Kept large PGCP data in place instead of moving it.
- Moved PGCP raw JSON downloader files into `scripts/importers/pgcp/`.
- Added `tests/pgcp/` for the downloader unit tests.
- Added documentation for data sources, developer operations, and data directory policy.

## 2026-06-17 to 2026-06-18

- Completed the first Arabidopsis thaliana PGCP raw JSON crawl.
- Final usable JSON count after retry: `26802 / 27655`.
- PGCP API later returned HTTP 500 and timeout responses. New bulk crawls are paused until API health checks return HTTP 200.
