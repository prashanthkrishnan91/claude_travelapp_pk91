"""Production entry point for the Travel Concierge FastAPI backend.

Run with:
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

from app.main import app  # noqa: F401, E402 — re-exported for uvicorn
