"""FastAPI application exposing ingestion, annotation and rendering APIs.

Also re-exports selected pipeline helpers so tests can monkeypatch them via
``api.app`` import path (backwards compatibility with older layout).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Re-export for tests to patch
from pipeline.ingestion.core import extract_and_chapterize  # noqa: F401
from pipeline.ingestion.pdf import detect_available_backends  # noqa: F401

from .routes.annotation import router as annotation_router
from .routes.ingest import router as ingest_router
from .routes.jobs import router as jobs_router
from .routes.listing import router as listing_router
from .routes.purge import router as purge_router
from .routes.render import router as render_router

app = FastAPI(title="Auto Audiobook Maker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(jobs_router)
app.include_router(listing_router)
app.include_router(annotation_router)
app.include_router(render_router)
app.include_router(purge_router)
