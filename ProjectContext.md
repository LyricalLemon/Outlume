# Project Outlume: Etsy Market Research Aggregator
## Context & Development Plan

### 1. Project Overview
**Name:** Outlume
**Goal:** Build a "lean" Everbee/ListingView alternative. A strictly personal, internal, non-commercial market research tool that pulls public Etsy listing data, tracks it over time, and aggregates the data to highlight outliers, high-velocity products, and top-performing keyword tags. The hosted web interface acts entirely as an internal data dashboard, not a commercial SaaS product, to strictly comply with Etsy's Personal Access Tier API policies.
**Constraint:** Must operate entirely on public data using the Etsy Open API v3 (Personal Access Tier - 10,000 requests/day). No commercialization or external user access.

---

### 2. Architecture & Tech Stack (Recommended for MVP)
* **Backend / Cron Jobs:** Python (ideal for data manipulation/cron jobs) or Node.js.
* **Database:** SQLite (fastest for MVP) or PostgreSQL (better for long-term time-series data).
* **Frontend:** Lightweight HTML/Vanilla JS with a data grid library (e.g., AG Grid, DataTables) or a simple React/Next.js dashboard.
* **API Integration:** Standard HTTP requests handling API keys via environment variables (no OAuth required).

---

### 3. Data Extraction Strategy
**Target Endpoints:**
* `GET /application/listings/active` (For pulling general niche data)
* `GET /application/listings/{listing_id}` (For specific tracking)

**Key Data Points to Extract & Store:**
* `listing_id` (Primary Key)
* `title`
* `tags` (Array of keywords)
* `price`
* `views` (Lifetime views)
* `num_favorers` (Lifetime favorites)
* `creation_tsz` (Timestamp of creation)

**Rate Limit Management:**
To respect the 10,000 daily limit, Outlume will batch requests. Tracking 1,000 listings updated once every 24 hours consumes only 10% of the daily allowance.

---

### 4. Database Schema
You will need a relational setup to track changes over time (Time-Series).

**Table 1: `Listings` (Static/Slow-changing data)**
* `listing_id` (INT, PK)
* `title` (TEXT)
* `tags` (JSON/TEXT)
* `creation_date` (DATE)
* `niche_category` (TEXT)

**Table 2: `Daily_Metrics` (The Time-Series tracking)**
* `id` (INT, PK)
* `listing_id` (INT, FK)
* `date_recorded` (DATE)
* `views` (INT)
* `favorites` (INT)

---

### 5. Algorithm Breakdown: "The Secret Sauce"
Because Etsy does not provide actual sales volume, Outlume must reverse-engineer traction using public metrics. 

#### A. Daily Velocity Calculation
The cron job runs daily at midnight to log the new `views` and `favorites`. 
* **Favorites Velocity:** `Favorites Today - Favorites Yesterday`
* **Views Velocity:** `Views Today - Views Yesterday`

#### B. Sales Estimation Formula (The Industry Standard Hack)
Different niches have different conversion rates, but a solid baseline estimation model is:
* `Estimated Daily Sales = Daily Favorites Velocity * Conversion Multiplier`
* *(Note: A standard multiplier is usually between 1.5 to 3 sales per favorite, depending on price point. You can tune this multiplier as you test niches).*

#### C. The Outlier Score (Finding the Hidden Gems)
To find products that are exploding in popularity despite being brand new, use this formula:
* `Days Active = Current Date - creation_tsz`
* `Traction Ratio = Total Favorites / Days Active`
* **Outlier Score** = `Traction Ratio * (Favorites Velocity over last 7 days)`
* *Why this works:* A 3-year-old listing with 5,000 favorites might be dead now. A 14-day-old listing with 200 favorites has massive velocity and a high Outlier Score.

#### D. Keyword Tag Extraction
When a niche is queried, pull the `tags` array from the top 50 fastest-growing listings.
* Flatten the arrays into one massive list.
* Count the frequency of each string.
* Display the top 10 most frequently used tags. These are the validated, high-converting keywords.

---

### 6. Implementation Steps for Antigravity IDE
1.  **Environment Setup:** Create `.env` file for `ETSY_API_KEY`.
2.  **DB Initialization:** Write a script to create the SQLite database and tables.
3.  **API Wrapper:** Write a function `fetch_etsy_listings(keyword)` that handles the GET request and parses the JSON.
4.  **Seed Script:** Run a one-time search for 5 niches and save the top 200 listings to the `Listings` table.
5.  **Tracker Script:** Write `daily_update.py` to loop through saved `listing_id`s, fetch their current views/favorites, and log them in `Daily_Metrics`.
6.  **Analysis Script:** Write the SQL queries to calculate the Outlier Score and Tag Frequencies.
7.  **Frontend Generation:** Display the results in a simple HTML table sorted by Outlier Score.
