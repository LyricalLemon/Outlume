from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .scheduler import start_scheduler
from .routers import listings, niches, metrics, analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Outlume API...")
    start_scheduler()
    yield
    logger.info("Shutting down Outlume API...")

app = FastAPI(title="Outlume API", lifespan=lifespan)

# Allow local HTML files to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listings.router, prefix="/api/listings", tags=["Listings"])
app.include_router(niches.router, prefix="/api/niches", tags=["Niches"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
