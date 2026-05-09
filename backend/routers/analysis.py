from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..services.analysis import get_outliers, get_top_tags

router = APIRouter()

@router.get("/outliers")
def fetch_outliers(limit: int = 50, niche_id: Optional[int] = None):
    try:
        outliers = get_outliers(limit=limit, niche_id=niche_id)
        return {"outliers": outliers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tags")
def fetch_top_tags(niche_id: int, limit: int = 10):
    try:
        tags = get_top_tags(niche_id=niche_id, limit=limit)
        return {"tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
