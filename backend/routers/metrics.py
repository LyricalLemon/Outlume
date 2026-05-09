from fastapi import APIRouter
from ..database import get_db

router = APIRouter()

@router.get("/{listing_id}")
def get_metrics(listing_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date_recorded, views, favorites, price
        FROM Daily_Metrics
        WHERE listing_id = ?
        ORDER BY date_recorded ASC
    """, (listing_id,))
    rows = cursor.fetchall()
    conn.close()
    return {"metrics": [dict(row) for row in rows]}
