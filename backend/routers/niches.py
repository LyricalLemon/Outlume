from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..services.seed import run_seed

router = APIRouter()

class SeedRequest(BaseModel):
    keyword: str
    sort_on: str = "score"

@router.get("/")
def get_niches():
    conn = get_db()
    cursor = conn.cursor()
    # Return niches with count of listings
    cursor.execute("""
        SELECT n.id, n.keyword, COUNT(ln.listing_id) as listing_count
        FROM Niches n
        LEFT JOIN Listing_Niches ln ON n.id = ln.niche_id
        GROUP BY n.id
    """)
    rows = cursor.fetchall()
    conn.close()
    return {"niches": [dict(row) for row in rows]}

@router.post("/seed")
async def seed_niche(request: SeedRequest, background_tasks: BackgroundTasks):
    """
    Triggers a seed operation in the background so the request doesn't block.
    """
    background_tasks.add_task(run_seed, request.keyword, request.sort_on)
    return {"message": f"Seed job for '{request.keyword}' started in the background."}
