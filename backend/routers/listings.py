from fastapi import APIRouter, HTTPException
from ..database import get_db

router = APIRouter()

@router.get("/")
def get_listings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Listings ORDER BY added_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return {"listings": [dict(row) for row in rows]}

@router.get("/{listing_id}")
def get_listing(listing_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Listings WHERE listing_id = ?", (listing_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found")
    return dict(row)
