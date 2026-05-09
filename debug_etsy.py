import asyncio
import sys
from backend.services.etsy_client import fetch_etsy_listings

async def main():
    listings = await fetch_etsy_listings("candles", max_pages=1)
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
