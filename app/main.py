"""FastAPI application entry-point."""

import os
import asyncio
from app import ecosystem
from app.performance import snapshots

ecosystem.install(snapshots)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import SESSION_SECRET, SESSION_COOKIE, ROOT_PATH, PRODUCTION
from app.database import init_db, database_ready
from app.routes import public, student, admin, api
from app.operations import UpdateGate

@asynccontextmanager
async def lifespan(app):
    init_db()
    stop = asyncio.Event()
    worker = asyncio.create_task(ecosystem.sync_worker(stop))
    try:
        yield
    finally:
        stop.set()
        await worker


app = FastAPI(title="Quacktuaries", docs_url=None, redoc_url=None,
              openapi_url=None, root_path=ROOT_PATH, lifespan=lifespan)

# Shared identity resolves once per request; app cookies still own classroom seats.
app.add_middleware(ecosystem.AccountMiddleware)
app.include_router(ecosystem.router)

# Signed-cookie sessions
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=86400 * 7,
                   session_cookie=SESSION_COOKIE, path=ROOT_PATH or "/",
                   https_only=PRODUCTION, same_site="lax")
app.add_middleware(UpdateGate)

# Static files
_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# Routers
app.include_router(public.router)
app.include_router(student.router)
app.include_router(admin.router)
app.include_router(api.router)


@app.get("/_health", include_in_schema=False)
def health():
    ready = database_ready()
    return JSONResponse({"status": "ok" if ready else "unavailable"},
                        status_code=200 if ready else 503,
                        headers={"Cache-Control": "no-store"})
