import asyncio
import logging
from datetime import datetime
from ..database import get_db
from ..services.etsy_client import fetch_listing_details

logger = logging.getLogger(__name__)

async def daily_update():
    """
    Loops all listing_ids, fetches current data, writes to Daily_Metrics.
    Logs success/failure per run to Job_Runs.
    Handles partial failures gracefully.
    """
    logger.info("Starting daily_update job...")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT listing_id FROM Listings")
    listings = cursor.fetchall()
    
    total_listings = len(listings)
    success_count = 0
    today = datetime.now().strftime('%Y-%m-%d')
    
    if total_listings == 0:
        logger.info("No listings found to track.")
        cursor.execute(
            "INSERT INTO Job_Runs (job_name, status, listings_processed, error_message) VALUES (?, ?, ?, ?)",
            ("daily_update", "success", 0, "No listings in database")
        )
        conn.commit()
        conn.close()
        return

    error_messages = []

    for row in listings:
        listing_id = row['listing_id']
        try:
            details = await fetch_listing_details(listing_id)
            if details:
                cursor.execute("""
                    INSERT OR IGNORE INTO Daily_Metrics (listing_id, date_recorded, views, favorites, price)
                    VALUES (?, ?, ?, ?, ?)
                """, (listing_id, today, details.views, details.num_favorers, details.price.float_value))
                success_count += 1
            else:
                error_messages.append(f"Listing {listing_id} not found.")
                
        except Exception as e:
            logger.error(f"Failed to update listing {listing_id}: {str(e)}")
            error_messages.append(f"Listing {listing_id} error: {str(e)}")
            
        # Delay to safely stay under the 5 QPS rate limit
        await asyncio.sleep(0.25)
        
    status = "success" if success_count == total_listings else ("partial_failure" if success_count > 0 else "failure")
    
    err_msg = "; ".join(error_messages[:5]) 
    if len(error_messages) > 5:
        err_msg += f" (and {len(error_messages) - 5} more)"
    
    cursor.execute(
        "INSERT INTO Job_Runs (job_name, status, listings_processed, error_message) VALUES (?, ?, ?, ?)",
        ("daily_update", status, success_count, err_msg if err_msg else None)
    )
    conn.commit()
    conn.close()
    
    logger.info(f"Finished daily_update. Processed {success_count}/{total_listings} successfully.")

if __name__ == "__main__":
    # Configure basic logging for manual runs
    logging.basicConfig(level=logging.INFO)
    asyncio.run(daily_update())
