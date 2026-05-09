# Project Outlume: Etsy Market Research Aggregator
## Context & Development Plan

### 1. Project Overview
**Name:** Outlume
**Goal:** Build a "lean" Everbee/ListingView alternative. A strictly personal, internal, non-commercial market research tool that pulls public Etsy listing data, tracks it over time, and aggregates the data to highlight outliers, high-velocity products, and top-performing keyword tags. The hosted web interface acts entirely as an internal data dashboard, not a commercial SaaS product, to strictly comply with Etsy's Personal Access Tier API policies.
**Constraint:** Must operate entirely on public data using the Etsy Open API v3 (Personal Access Tier - 5,000 requests/day). No commercialization or external user access.

---

### 2. Architecture & Tech Stack (Finalised)

| Layer | Decision | Rationale |
|---|---|---|
| Backend framework | **FastAPI** | Frontend is a separate app calling a REST API. FastAPI provides async support, automatic `/docs` API explorer, and Pydantic for validating Etsy API responses at the boundary. Flask has none of these. |
| Scheduler | **APScheduler** (embedded in FastAPI process) | Running locally — no system cron or process manager needed. APScheduler runs inside the app. |
| HTTP client | **httpx** | Async-native, pairs cleanly with FastAPI's async handlers. |
| Database | **SQLite with WAL mode enabled** | Scale maths confirmed: 1,000 listings × 365 days = 365,000 rows in `Daily_Metrics` at year one. SQLite handles this comfortably. WAL mode is non-negotiable — enabled on first DB connection, not optionally. |
| Query layer | **Raw sqlite3 with explicit SQL** | Keeps time-series queries visible and debuggable. No ORM abstraction hiding what's happening. SQLAlchemy overhead not justified at this scale. |
| Data validation | **Pydantic v2** | Validates all Etsy API responses at the boundary. Silent field changes in the Etsy API surface immediately rather than corrupting data silently. |
| Frontend | **Plain HTML/Vanilla JS** (no build step) | Opens directly in browser. No Vite, no bundler, no build step for MVP. Upgrade path to Vite exists when warranted. |
| Environment config | **python-dotenv** | `ETSY_API_KEY` lives in `.env`, never hardcoded, never committed. |

**Runtime environment:** Local machine (Mac/Linux), single process, no concurrent users.

---

### 3. Data Extraction Strategy

**Target Endpoints:**
* `GET /application/listings/active` — For pulling and seeding niche data
* `GET /application/listings/{listing_id}` — For daily tracking of specific listings

**Key Data Points to Extract & Store:**
* `listing_id` (Primary Key)
* `title`
* `tags` (Array of keywords — stored as JSON text)
* `price` (tracked daily in `Daily_Metrics` — sellers reprice frequently)
* `views` (Lifetime views)
* `num_favorers` (Lifetime favorites)
* `creation_tsz` (Timestamp of listing creation)

**Rate Limit Management:**
Personal Access Tier allows 5,000 requests/day. Tracking 1,000 listings updated once per 24 hours = 1,000 requests = 20% of daily allowance. Remaining 80% available for seeding, re-seeding, and ad-hoc queries.

**Seed Sort Strategy:**
The seed script supports all three of Etsy's `sort_on` options, selectable at run time:
* `score` — Etsy relevance ranking (what buyers actually see)
* `num_favorers` — Most favorited (established traction)
* `created` — Newest listings (early movers)

Because the same listing can appear across multiple sort runs, the seed script deduplicates on `listing_id` before inserting. The sort method used is stored in `seed_sort_origin` on the `Listings` table so the population context is never lost.

---

### 4. Database Schema (Finalised)

#### Design Decisions
- `price` moves to `Daily_Metrics` — Etsy sellers reprice constantly; a static snapshot is misleading.
- `niche_category` is removed from `Listings` — replaced by a proper many-to-many relationship via a `Listing_Niches` junction table. One listing can belong to multiple niches if it surfaces across multiple seed runs.
- `seed_sort_origin` added to `Listings` — records which sort method seeded this listing (`score`, `num_favorers`, or `created`).
- `Job_Runs` table added — audit log for every scheduler execution. Tracks success/failure, listings processed, and error messages. Silent failures are not acceptable.
- All indexes defined at init time — not bolted on later. The composite unique index on `Daily_Metrics(listing_id, date_recorded)` serves two purposes: it prevents duplicate daily rows if the tracker runs twice, and it makes 7-day velocity window queries fast.

#### Schema

```sql
-- Enable WAL mode on every connection (set in database.py, not here)
PRAGMA journal_mode=WAL;

-- Niche keywords — unique, reusable across multiple seed runs
CREATE TABLE Niches (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE
);

-- Core listing data (static / slow-changing)
CREATE TABLE Listings (
    listing_id       INTEGER PRIMARY KEY,
    title            TEXT NOT NULL,
    tags             TEXT NOT NULL,        -- JSON array stored as text
    creation_date    DATE NOT NULL,
    seed_sort_origin TEXT NOT NULL,        -- 'score' | 'num_favorers' | 'created'
    added_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Many-to-many: one listing can belong to multiple niches
CREATE TABLE Listing_Niches (
    listing_id  INTEGER NOT NULL REFERENCES Listings(listing_id),
    niche_id    INTEGER NOT NULL REFERENCES Niches(id),
    PRIMARY KEY (listing_id, niche_id)
);

-- Daily time-series snapshots
CREATE TABLE Daily_Metrics (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id    INTEGER NOT NULL REFERENCES Listings(listing_id),
    date_recorded DATE NOT NULL,
    views         INTEGER NOT NULL,
    favorites     INTEGER NOT NULL,
    price         REAL NOT NULL            -- tracked here, not on Listings
);

-- Scheduler audit log
CREATE TABLE Job_Runs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_name            TEXT NOT NULL,
    status              TEXT NOT NULL,     -- 'success' | 'failure'
    listings_processed  INTEGER,
    error_message       TEXT               -- NULL on success
);

-- Indexes (defined at init time — non-negotiable)
CREATE UNIQUE INDEX idx_daily_metrics_listing_date
    ON Daily_Metrics(listing_id, date_recorded);   -- fast 7-day window + prevents duplicates

CREATE INDEX idx_listings_creation
    ON Listings(creation_date);                    -- Outlier Score: days_active calculation

CREATE INDEX idx_job_runs_run_at
    ON Job_Runs(run_at);
```

---

### 5. Algorithm Breakdown: "The Secret Sauce"

Because Etsy does not expose actual sales volume, Outlume reverse-engineers traction using public metrics.

#### A. Daily Velocity Calculation
The APScheduler job runs daily. On each run it fetches current `views`, `favorites`, and `price` for every tracked listing and logs a new row in `Daily_Metrics`.

* **Favorites Velocity:** `Favorites Today - Favorites Yesterday`
* **Views Velocity:** `Views Today - Views Yesterday`

#### B. Sales Estimation Formula
* `Estimated Daily Sales = Daily Favorites Velocity × Conversion Multiplier`
* Default multiplier: **1.5–3.0** (tunable per niche via the Settings page). Higher price points trend toward the lower end of the range.

#### C. The Outlier Score (Finding the Hidden Gems)
* `Days Active = Current Date - creation_date`
* `Traction Ratio = Total Favorites / Days Active`
* `7-Day Favorites Velocity = SUM of daily favorites deltas over last 7 Daily_Metrics rows`
* **Outlier Score** = `Traction Ratio × 7-Day Favorites Velocity`

*Why this works:* A 3-year-old listing with 5,000 favorites may be stagnant. A 14-day-old listing with 200 favorites and accelerating daily gains scores dramatically higher. Age and momentum are both weighted.

*Query note:* The `UNIQUE INDEX on Daily_Metrics(listing_id, date_recorded)` makes the 7-row window lookup fast at scale.

#### D. Keyword Tag Extraction
1. Query the top 50 fastest-growing listings by `7-Day Favorites Velocity` within a niche.
2. Flatten all `tags` arrays from those listings into a single list.
3. Count tag frequency across the full list.
4. Return the top 10 most frequently occurring tags — these are the validated, high-signal keywords for that niche.

---

### 6. Directory Structure

```
outlume/
├── .env                        # ETSY_API_KEY — never committed
├── .gitignore
├── requirements.txt
├── README.md
│
├── backend/
│   ├── main.py                 # FastAPI entry point — mounts routers, starts scheduler
│   ├── config.py               # Loads .env, exposes typed Settings object via pydantic-settings
│   ├── database.py             # SQLite connection factory, WAL mode pragma, get_db()
│   │
│   ├── models/
│   │   └── etsy.py             # Pydantic models for Etsy API response validation
│   │
│   ├── routers/
│   │   ├── listings.py         # GET /listings, GET /listings/{id}
│   │   ├── niches.py           # GET /niches, POST /niches/seed
│   │   ├── metrics.py          # GET /metrics/{listing_id}
│   │   └── analysis.py         # GET /analysis/outliers, GET /analysis/tags
│   │
│   ├── services/
│   │   ├── etsy_client.py      # fetch_etsy_listings() — pagination, rate limiting, retries
│   │   ├── seed.py             # One-time seed logic — deduplication, junction table inserts
│   │   ├── tracker.py          # daily_update() — loops listings, writes Daily_Metrics rows
│   │   └── analysis.py         # Outlier score calc, tag frequency aggregation
│   │
│   ├── scheduler.py            # APScheduler config — registers and starts daily_update job
│   │
│   └── db/
│       ├── init_db.py          # Creates all tables, indexes, enables WAL mode
│       └── outlume.db          # SQLite file (gitignored)
│
└── frontend/
    ├── index.html              # Dashboard — top listings by Outlier Score
    ├── tracking.html           # Tracked listings view
    ├── keywords.html           # Keyword analyser
    ├── settings.html           # Settings — niche management, conversion multiplier
    └── assets/
        ├── css/
        │   └── main.css
        └── js/
            ├── api.js          # All fetch() calls to FastAPI — single source of truth
            ├── dashboard.js
            ├── tracking.js
            ├── keywords.js
            └── settings.js
```

---

### 7. Python Dependencies (`requirements.txt`)

```
fastapi
uvicorn[standard]
httpx
pydantic-settings
python-dotenv
apscheduler
```

No ORM. No pandas at MVP — outlier score and tag aggregation are handled in SQL. Pandas is introduced only if analysis logic outgrows what clean SQL can express.

---

### 8. Implementation Order

Build in strict dependency order — each step must be working before the next begins.

1. **Environment Setup** — Create `.env` with `ETSY_API_KEY`. Create `.gitignore`. Install dependencies.
2. **DB Initialisation** — Write and run `init_db.py`. Verify all tables, indexes, and WAL mode via SQLite CLI before proceeding.
3. **API Wrapper** — Write `etsy_client.py`: `fetch_etsy_listings(keyword, sort_on, page)`. Handle pagination (100 results/page, 2 pages max), rate limit headers, and HTTP errors. Validate responses with Pydantic models.
4. **Seed Script** — Write `seed.py`. Accept a keyword and sort method as arguments. Deduplicate on `listing_id`. Insert into `Listings`, `Niches`, and `Listing_Niches`. Log to `Job_Runs`.
5. **Tracker Script** — Write `tracker.py`: `daily_update()`. Loop all `listing_id`s, fetch current data, write to `Daily_Metrics`. Log success/failure per run to `Job_Runs`. Handle partial failures gracefully — one bad listing should not abort the full run.
6. **Scheduler** — Wire `daily_update()` into APScheduler in `scheduler.py`. Start alongside FastAPI in `main.py`.
7. **Analysis Queries** — Write SQL for Outlier Score and Tag Frequency. Expose via `/analysis/outliers` and `/analysis/tags` endpoints.
8. **FastAPI Routers** — Build all four routers. Enable CORS for local HTML file access.
9. **Frontend** — Build HTML/JS pages. All API calls centralised in `api.js`. Pages: `/dashboard`, `/tracking`, `/keywords`, `/settings`.