"""FastAPI entrypoint: `uv run uvicorn app.main:app --reload`."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config, db
from app.routes import admin, admin_logs, public

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="School AI Assistant", lifespan=lifespan, docs_url=None, redoc_url=None)
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(admin_logs.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(config.STATIC_DIR / "index.html")


@app.get("/admin")
def admin_page():
    return FileResponse(config.STATIC_DIR / "admin.html")


app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
