"""Travel Concierge — FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routes import cards_router, compare_router, deals_router, itinerary_router, search_router, trips_router, value_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Backend API for the Travel Concierge app — manage trips, "
        "itineraries, and travel cards with cash + points dual pricing."
    ),
    debug=settings.debug,
)

# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------

# CORS — allow_credentials cannot be True when allow_origins=["*"]
# allow_origin_regex covers all Vercel preview & production deployments
# without needing to enumerate individual URLs in env vars.
if settings.cors_allow_all:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"https://[a-zA-Z0-9\-]+\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

app.include_router(trips_router)
app.include_router(itinerary_router)
app.include_router(cards_router)
app.include_router(compare_router)
app.include_router(deals_router)
app.include_router(search_router)
app.include_router(value_router)

# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------

@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe — returns 200 when the process is up."""
    return {"status": "ok", "app": settings.app_name}
