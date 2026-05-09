import httpx
import logging
from typing import List, Optional
from ..config import get_settings
from ..models.etsy import EtsyListingsResponse, EtsyListing

logger = logging.getLogger(__name__)

BASE_URL = "https://api.etsy.com/v3/application"

async def fetch_etsy_listings(keyword: str, sort_on: str = "score", max_pages: int = 2) -> List[EtsyListing]:
    """
    Fetch listings from Etsy based on a keyword.
    sort_on can be 'score', 'num_favorers', or 'created'.
    Handles pagination (up to max_pages, 100 results/page).
    """
    settings = get_settings()
    headers = {
        "x-api-key": settings.ETSY_API_KEY
    }
    
    all_listings = []
    
    async with httpx.AsyncClient() as client:
        for page in range(1, max_pages + 1):
            url = f"{BASE_URL}/listings/active"
            params = {
                "keywords": keyword,
                "sort_on": sort_on,
                "limit": 100,
                "offset": (page - 1) * 100,
            }
            
            logger.info(f"Fetching page {page} for keyword '{keyword}' (sort: {sort_on})")
            
            try:
                response = await client.get(url, headers=headers, params=params, timeout=15.0)
                response.raise_for_status()
                
                # Check rate limits (for debugging)
                remaining = response.headers.get("X-RateLimit-Remaining")
                if remaining:
                    logger.debug(f"Etsy API Rate Limit Remaining: {remaining}")
                
                data = response.json()
                parsed_response = EtsyListingsResponse(**data)
                
                all_listings.extend(parsed_response.results)
                
                # If there are fewer than 100 results, we've hit the end
                if len(parsed_response.results) < 100:
                    break
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
                break
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")
                break
                
    return all_listings

async def fetch_listing_details(listing_id: int) -> Optional[EtsyListing]:
    """
    Fetch a specific listing's details for daily tracking.
    """
    settings = get_settings()
    headers = {
        "x-api-key": settings.ETSY_API_KEY
    }
    
    url = f"{BASE_URL}/listings/{listing_id}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            
            if response.status_code == 404:
                logger.warning(f"Listing {listing_id} not found (might be inactive/deleted).")
                return None
                
            response.raise_for_status()
            
            data = response.json()
            return EtsyListing(**data)
            
        except Exception as e:
            logger.error(f"Error fetching listing {listing_id}: {str(e)}")
            return None
