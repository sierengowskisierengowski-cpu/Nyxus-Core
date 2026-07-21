import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import auth, config
from app.database import init_db
from app.routers import auth as auth_router
from app.routers import dashboard, execute, notes, runs, tools

logger = logging.getLogger("gsl")


@asynccontextmanager
async def lifespan(app: FastAPI):
    auth.configure()
    logging.basicConfig(level=logging.INFO)
    logger.info("\n%s", auth.startup_banner())
    await init_db()
    yield


app = FastAPI(title="GowskiNet Security Lab API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,  # token auth via Authorization header, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public: auth + health. Everything else requires a valid session token.
app.include_router(auth_router.router)

_protected = [Depends(auth.require_auth)]
app.include_router(tools.router, dependencies=_protected)
app.include_router(runs.router, dependencies=_protected)
app.include_router(notes.router, dependencies=_protected)
app.include_router(dashboard.router, dependencies=_protected)
# execute.router carries its own per-route auth (the WebSocket authenticates via
# a query-param token because browsers can't set Authorization on WS handshakes).
app.include_router(execute.router)


@app.get("/api/healthz")
async def healthz():
    return {"status": "ok"}


# ── Optional: serve the built SPA so the whole app runs on one port ───────────
# Mounted last so it never shadows /api or /ws routes.
if config.STATIC_DIR and os.path.isdir(config.STATIC_DIR):
    app.mount("/", StaticFiles(directory=config.STATIC_DIR, html=True), name="spa")
    logger.info("Serving built SPA from %s", config.STATIC_DIR)
