import sqlite3
import json
from collections import Counter
from typing import List, Dict, Any
from ..database import get_db

def get_outliers(limit: int = 50, niche_id: int = None) -> List[Dict[str, Any]]:
    """
    Calculates and returns the top listings based on the Outlier Score.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        WITH LatestMetrics AS (
            SELECT listing_id, favorites, views, price, date_recorded
            FROM (
                SELECT listing_id, favorites, views, price, date_recorded,
                       ROW_NUMBER() OVER (PARTITION BY listing_id ORDER BY date_recorded DESC) as rn
                FROM Daily_Metrics
            ) WHERE rn = 1
        ),
        Velocity7Day AS (
            SELECT listing_id, 
                   MAX(favorites) - MIN(favorites) as fav_velocity_7d,
                   MAX(views) - MIN(views) as views_velocity_7d
            FROM (
                SELECT listing_id, favorites, views,
                       ROW_NUMBER() OVER (PARTITION BY listing_id ORDER BY date_recorded DESC) as rn
                FROM Daily_Metrics
            ) WHERE rn <= 7
            GROUP BY listing_id
        )
        SELECT 
            l.listing_id,
            l.title,
            l.creation_date,
            l.seed_sort_origin,
            lm.price,
            CAST(julianday('now') - julianday(l.creation_date) AS INTEGER) as days_active,
            lm.favorites as total_favorites,
            lm.views as total_views,
            v.fav_velocity_7d,
            v.views_velocity_7d,
            (CAST(lm.favorites AS REAL) / MAX(CAST(julianday('now') - julianday(l.creation_date) AS INTEGER), 1)) * v.fav_velocity_7d AS outlier_score
        FROM Listings l
        JOIN LatestMetrics lm ON l.listing_id = lm.listing_id
        JOIN Velocity7Day v ON l.listing_id = v.listing_id
    """
    
    params = []
    if niche_id is not None:
        query += " JOIN Listing_Niches ln ON l.listing_id = ln.listing_id WHERE ln.niche_id = ?"
        params.append(niche_id)
        
    query += " ORDER BY outlier_score DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_top_tags(niche_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Query the top 50 fastest-growing listings by 7-Day Favorites Velocity within a niche.
    Flatten all tags arrays, count frequency, and return top tags.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        WITH Velocity7Day AS (
            SELECT listing_id, 
                   MAX(favorites) - MIN(favorites) as fav_velocity_7d
            FROM (
                SELECT listing_id, favorites,
                       ROW_NUMBER() OVER (PARTITION BY listing_id ORDER BY date_recorded DESC) as rn
                FROM Daily_Metrics
            ) WHERE rn <= 7
            GROUP BY listing_id
        )
        SELECT l.tags
        FROM Listings l
        JOIN Velocity7Day v ON l.listing_id = v.listing_id
        JOIN Listing_Niches ln ON l.listing_id = ln.listing_id
        WHERE ln.niche_id = ?
        ORDER BY v.fav_velocity_7d DESC
        LIMIT 50
    """
    
    cursor.execute(query, (niche_id,))
    rows = cursor.fetchall()
    conn.close()
    
    tag_counter = Counter()
    for row in rows:
        tags = json.loads(row['tags'])
        tag_counter.update(tags)
        
    top_tags = tag_counter.most_common(limit)
    return [{"tag": tag, "frequency": count} for tag, count in top_tags]
