import sqlite3
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "outlume.db")

SCHEMA = """
-- Enable WAL mode
PRAGMA journal_mode=WAL;

-- Niche keywords — unique, reusable across multiple seed runs
CREATE TABLE IF NOT EXISTS Niches (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE
);

-- Core listing data (static / slow-changing)
CREATE TABLE IF NOT EXISTS Listings (
    listing_id       INTEGER PRIMARY KEY,
    title            TEXT NOT NULL,
    tags             TEXT NOT NULL,        -- JSON array stored as text
    creation_date    DATE NOT NULL,
    seed_sort_origin TEXT NOT NULL,        -- 'score' | 'num_favorers' | 'created'
    added_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Many-to-many: one listing can belong to multiple niches
CREATE TABLE IF NOT EXISTS Listing_Niches (
    listing_id  INTEGER NOT NULL REFERENCES Listings(listing_id),
    niche_id    INTEGER NOT NULL REFERENCES Niches(id),
    PRIMARY KEY (listing_id, niche_id)
);

-- Daily time-series snapshots
CREATE TABLE IF NOT EXISTS Daily_Metrics (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id    INTEGER NOT NULL REFERENCES Listings(listing_id),
    date_recorded DATE NOT NULL,
    views         INTEGER NOT NULL,
    favorites     INTEGER NOT NULL,
    price         REAL NOT NULL            -- tracked here, not on Listings
);

-- Scheduler audit log
CREATE TABLE IF NOT EXISTS Job_Runs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_name            TEXT NOT NULL,
    status              TEXT NOT NULL,     -- 'success' | 'failure'
    listings_processed  INTEGER,
    error_message       TEXT               -- NULL on success
);

-- Indexes (defined at init time — non-negotiable)
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_metrics_listing_date
    ON Daily_Metrics(listing_id, date_recorded);   -- fast 7-day window + prevents duplicates

CREATE INDEX IF NOT EXISTS idx_listings_creation
    ON Listings(creation_date);                    -- Outlier Score: days_active calculation

CREATE INDEX IF NOT EXISTS idx_job_runs_run_at
    ON Job_Runs(run_at);
"""

def init_db():
    print(f"Initializing database at: {DB_PATH}")
    # Connecting to the database will create it if it doesn't exist
    conn = sqlite3.connect(DB_PATH)
    
    # Enable WAL mode for the DB creation/initialization
    conn.execute("PRAGMA journal_mode=WAL;")
    
    # Execute schema creation
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    
    print("Database initialization complete.")
    print("Checking created tables...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables found:", [t[0] for t in tables])
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = cursor.fetchall()
    print("Indexes found:", [i[0] for i in indexes if not i[0].startswith('sqlite_autoindex')])
    
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    print(f"Journal mode: {mode}")
    
    conn.close()

if __name__ == "__main__":
    init_db()
