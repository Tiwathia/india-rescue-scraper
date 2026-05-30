# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## What this project is

**india-rescue-scraper** is a small Python web-scraping service that aggregates
disaster/rescue-related news for India (originally built around the Sikkim
landslide/flood events) from Indian government portals, news outlets, and
Twitter. It exposes the results through a FastAPI HTTP API that is designed to
be consumed as a **Custom GPT Action** (see `static/`), plus a standalone
Streamlit dashboard for browsing Twitter results.

The API is intended to be deployed to Render (`https://india-rescue-scraper.onrender.com`).

## Layout

| Path | Purpose |
| --- | --- |
| `main.py` | The FastAPI application. All scrapers and HTTP endpoints live here. |
| `dashboard.py` | Standalone Streamlit app that scrapes Twitter for Sikkim keywords and shows the latest tweets in a table. Not part of the API. |
| `static/action.json` | OpenAPI 3.1 spec (v1.2.0) used to register this API as a Custom GPT Action. Served at `/static/action.json`. |
| `static/openapi.yaml.txt` | Older (v1.1.0) YAML copy of the OpenAPI spec. Effectively legacy — keep in sync with `action.json` or remove if no longer used. |
| `requirements.txt` | Python dependencies. |
| `runtime.txt` | Pins the Python runtime (`python-3.11`) for the deploy platform. |
| `<runtime>` | Stray/leftover file also containing `python-3.11`. Likely an accidental commit; not referenced by anything. |
| `.devcontainer/devcontainer.json` | Codespaces/devcontainer config. Note: it runs the **Streamlit dashboard**, not the API. |
| `README.md` | One-line description. |

## Architecture

`main.py` is the heart of the project and follows a simple pattern:

1. **Data models** — `RescueUpdate` (title, summary, source, date, url) and
   `RescueUpdatesResponse` (a list of updates). All scraper output is normalized
   into `RescueUpdate`.
2. **Per-source scraper functions** — one `async def scrape_<source>(query)`
   per site (`scrape_pib`, `scrape_sikkim`, `scrape_ndtv`,
   `scrape_india_today`, `scrape_times_now`). Each:
   - fetches a page with `httpx.AsyncClient`,
   - parses it with `BeautifulSoup` using a CSS selector specific to that site's
     HTML,
   - filters items by case-insensitive substring match against `query`,
   - returns a `List[RescueUpdate]`,
   - wraps everything in `try/except` and prints an error (never raises) so one
     broken source doesn't take down the whole request.
3. **Twitter scraper** — `scrape_twitter_critical_terms()` is **synchronous**.
   It shells out to the `snscrape` CLI via `subprocess.Popen`, parses JSONL
   output, and filters to the last 72 hours. It uses a hard-coded list of
   query terms (names/hashtags) rather than the request `query`.
4. **Endpoints**:
   - `GET /rescue-updates?query=...` (`operation_id=fetchRescueUpdates`) — runs
     all scrapers, concatenates results, sorts by `date` descending, returns the
     top 10.
   - `GET /rss-summary` (`operation_id=getRssSummary`) — keyword-filtered
     headline scrape across several outlets. **See "Known issues" — this route
     is currently not registered correctly.**

There is no database, cache, or persistence — every request re-scrapes live.

## Conventions to follow

- **Adding a news source:** write a new `async def scrape_<name>(query)` that
  mirrors the existing scrapers (httpx + BeautifulSoup + per-item `query`
  substring filter + try/except that prints and swallows errors), returning
  `List[RescueUpdate]`. Then add a call to it inside `get_rescue_updates` and
  include its results in `all_updates`.
- **Normalize everything to `RescueUpdate`.** `url` is a `pydantic.HttpUrl`, so
  always build absolute URLs (prepend the site origin to relative `href`s, as
  the existing scrapers do) or pydantic validation will reject the response.
- **Dates** are strings formatted `"%Y-%m-%d"` and set to "now" for scraped
  pages (the source HTML rarely exposes a reliable timestamp). Sorting is
  lexicographic on this string, which works because of the ISO format.
- **Error handling:** individual scrapers must not raise; they log with a
  `print(f"[❌ <SOURCE> ERROR] {e}")` and return what they have. Keep this
  pattern so a single failing site degrades gracefully.
- **Selectors are brittle.** They target the current HTML of external sites and
  will silently return nothing when those sites change their markup. If a source
  stops returning results, re-inspect the live page's structure first.
- **Keep the OpenAPI spec in sync.** If you add, rename, or change an endpoint
  or its `operation_id`, update `static/action.json` (and bump its `version`) so
  the Custom GPT Action stays accurate. `operation_id`s in `main.py` and the
  spec must match.

## Running locally

The API and the dashboard are two separate entry points.

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the FastAPI API (default port 8000):

```bash
uvicorn main:app --reload
# Interactive docs at http://localhost:8000/docs
# Example: http://localhost:8000/rescue-updates?query=sikkim
```

Run the Streamlit dashboard (default port 8501):

```bash
streamlit run dashboard.py
```

The devcontainer's `postAttachCommand` launches the **Streamlit dashboard** on
port 8501, not the API — be aware of this when working in Codespaces.

## Deployment

- Target platform: Render (URL hard-coded in `static/action.json`'s `servers`).
- `runtime.txt` pins Python 3.11.
- Typical Render start command for the API would be
  `uvicorn main:app --host 0.0.0.0 --port $PORT`. There is no `Procfile` or
  Render config committed, so verify the deploy command on the platform itself.

## Known issues / gotchas (do not assume the code is clean)

- **`/rss-summary` is effectively unregistered.** In `main.py` the
  `@app.get("/rss-summary", ...)` decorator is indented *inside* the `except`
  block of `get_rescue_updates`, immediately after a `raise` (so it is
  unreachable dead code), while `async def get_rss_summary` is defined at module
  level with no decorator attached. As written, the route is not added to the
  app. If you need this endpoint, fix the indentation so the decorator sits at
  module level directly above the function. Be careful to preserve behavior when
  touching this area.
- **`snscrape` / Twitter scraping is unreliable.** `snscrape`'s Twitter backend
  frequently breaks due to upstream changes, and `dashboard.py` uses the
  `snscrape.modules.twitter` Python API while `main.py` uses the `snscrape` CLI.
  Expect Twitter results to often be empty.
- **No tests, linter config, or CI** are present in the repo. There is nothing
  to run to validate changes other than starting the app and hitting endpoints.
- The `<runtime>` file and `static/openapi.yaml.txt` appear to be leftovers;
  treat `runtime.txt` and `static/action.json` as the sources of truth.

## Git / workflow

- Default branch is `main`.
- Make changes on a feature branch and push with `git push -u origin <branch>`.
- Do not create pull requests unless explicitly asked.
- There is no automated check to gate commits; manually verify the app still
  starts (`uvicorn main:app`) after changes to `main.py`.
