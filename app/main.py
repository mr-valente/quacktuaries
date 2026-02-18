"""FastAPI application entry-point."""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import SESSION_SECRET
from app.database import init_db
from app.routes import public, student, admin

app = FastAPI(title="Quacktuaries", docs_url=None, redoc_url=None)

# Signed-cookie sessions
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=86400 * 7)

# Static files
_static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(_static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# Routers
app.include_router(public.router)
app.include_router(student.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup():
    init_db()
