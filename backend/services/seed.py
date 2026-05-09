import asyncio
import sqlite3
import argparse
import json
from datetime import datetime
from ..services.etsy_client import fetch_etsy_listings
from ..db.init_db import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

async def run_seed(keyword: str, sort_on: str = "score"):
    print(f"Starting seed for keyword '{keyword}' (sort_on: {sort_on})")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Ensure niche exists
    cursor.execute("INSERT OR IGNORE INTO Niches (keyword) VALUES (?)", (keyword,))
    cursor.execute("SELECT id FROM Niches WHERE keyword = ?", (keyword,))
    niche_id = cursor.fetchone()[0]
    
    listings = await fetch_etsy_listings(keyword, sort_on=sort_on, max_pages=2)
    
    if not listings:
        print("No listings found or API error.")
        cursor.execute(
            "INSERT INTO Job_Runs (job_name, status, listings_processed, error_message) VALUES (?, ?, ?, ?)",
            (f"seed_{keyword}", "failure", 0, "No listings returned from API")
        )
        conn.commit()
        conn.close()
        return

    # Deduplicate by listing_id in case the API returned duplicates
    unique_listings = {l.listing_id: l for l in listings}
    listings_to_process = list(unique_listings.values())
    
    success_count = 0
    try:
        for listing in listings_to_process:
            # Insert into Listings
            creation_date = datetime.fromtimestamp(listing.creation_timestamp).strftime('%Y-%m-%d')
            tags_json = json.dumps(listing.tags)
            
            cursor.execute("""
                INSERT OR IGNORE INTO Listings (listing_id, title, tags, creation_date, seed_sort_origin)
                VALUES (?, ?, ?, ?, ?)
            """, (listing.listing_id, listing.title, tags_json, creation_date, sort_on))
            
            # Insert into junction table
            cursor.execute("""
                INSERT OR IGNORE INTO Listing_Niches (listing_id, niche_id)
                VALUES (?, ?)
            """, (listing.listing_id, niche_id))
            
            # Efficiently insert the first day of metrics right away
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                INSERT OR IGNORE INTO Daily_Metrics (listing_id, date_recorded, views, favorites, price)
                VALUES (?, ?, ?, ?, ?)
            """, (listing.listing_id, today, listing.views, listing.num_favorers, listing.price.float_value))
            
            success_count += 1
            
        cursor.execute(
            "INSERT INTO Job_Runs (job_name, status, listings_processed, error_message) VALUES (?, ?, ?, ?)",
            (f"seed_{keyword}_{sort_on}", "success", success_count, None)
        )
        conn.commit()
        print(f"Successfully seeded {success_count} listings for '{keyword}'.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during seed: {str(e)}")
        cursor.execute(
            "INSERT INTO Job_Runs (job_name, status, listings_processed, error_message) VALUES (?, ?, ?, ?)",
            (f"seed_{keyword}_{sort_on}", "failure", success_count, str(e))
        )
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Outlume DB with Etsy listings.")
    parser.add_argument("keyword", help="Niche keyword to search for")
    parser.add_argument("--sort", default="score", choices=["score", "num_favorers", "created"], help="Sort method")
    args = parser.parse_args()
    
    # We must run this module via -m backend.services.seed so imports work
    asyncio.run(run_seed(args.keyword, sort_on=args.sort))
