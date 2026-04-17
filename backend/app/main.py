"""Travel Concierge — FastAPI application entry point."""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routes import cards_router, compare_router, context_router, deals_router, itinerary_router, resolve_router, search_router, trips_router, value_router

print("App starting...")

settings = get_settings()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("travel_concierge")

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

# CORS — allow all origins so the frontend at http://127.0.0.1:3000 can call directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Exception handlers — ensure all errors return JSON, not plain text
# ------------------------------------------------------------------

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler: return a JSON body instead of FastAPI's default plain-text 500."""
    exc_name = type(exc).__name__

    # Connection / network errors (Supabase unreachable, DNS failure, etc.)
    if exc_name in ("ConnectError", "ConnectTimeout", "ReadTimeout", "NetworkError",
                    "RemoteProtocolError", "PoolTimeout"):
        logger.warning("[503] %s %s — DB/network unreachable: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=503,
            content={"detail": f"Database temporarily unavailable ({exc_name}). Please try again."},
        )

    logger.exception("[500] Unhandled error in %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {exc_name}"},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every incoming request: method, path, body, and elapsed time."""
    body = b""
    try:
        body = await request.body()
    except Exception:
        pass

    body_text = body.decode("utf-8", errors="replace") if body else ""
    print(f"[REQ] {request.method} {request.url.path}  body={body_text or '<empty>'}")
    logger.debug("[REQUEST] %s %s  body=%s", request.method, request.url.path, body_text or "<empty>")

    start = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000)

    print(f"[RES] {request.method} {request.url.path} → {response.status_code} ({elapsed}ms)")
    logger.debug("[RESPONSE] %s %s → %s (%dms)", request.method, request.url.path, response.status_code, elapsed)
    return response


# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

app.include_router(trips_router)
app.include_router(itinerary_router)
app.include_router(cards_router)
app.include_router(compare_router)
app.include_router(context_router)
app.include_router(deals_router)
app.include_router(resolve_router)
app.include_router(search_router)
app.include_router(value_router)

print("Routes loaded")


# ------------------------------------------------------------------
# Startup: print all registered routes + verify Supabase connection
# ------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    """Log all registered routes and verify Supabase connectivity on boot."""
    logger.info("=== Registered routes ===")
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", str(route))
        if methods:
            logger.info("  %-30s %s", path, sorted(methods))
        else:
            logger.info("  %s", path)
    logger.info("=========================")

    # Verify Supabase (or mock) client initialises without raising
    try:
        from app.db.client import get_supabase
        get_supabase()
        print("Supabase connected")
        logger.info("Supabase connected")
    except Exception as exc:  # pragma: no cover
        print(f"Supabase init warning: {exc}")
        logger.warning("Supabase init warning: %s", exc)


# ------------------------------------------------------------------
# Root + health check
# ------------------------------------------------------------------

@app.get("/", tags=["meta"])
def root() -> dict:
    """Root probe — confirms the API process is running."""
    return {"message": "API running"}


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe — returns 200 when the process is up."""
    return {"status": "ok", "app": settings.app_name}
