import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.auth import hash_password
from app.config import settings
from app.database import async_session, engine, Base
from app.models import User
from app.routers import auth, dashboard, agent_api, notifications
from app.services.alerts import evaluate_offline_agents


async def _alert_background_loop():
    while True:
        try:
            async with async_session() as session:
                await evaluate_offline_agents(session)
                await session.commit()
        except Exception:
            pass
        await asyncio.sleep(settings.alert_check_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == settings.default_admin_username))
        if not result.scalar_one_or_none():
            session.add(
                User(
                    username=settings.default_admin_username,
                    password_hash=hash_password(settings.default_admin_password),
                )
            )
            await session.commit()

    alert_task = asyncio.create_task(_alert_background_loop())
    yield
    alert_task.cancel()


app = FastAPI(title="Ubuntu Monitor", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(agent_api.router)
app.include_router(notifications.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


def _dashboard_static_dir() -> Path | None:
    if os.environ.get("UBUNTU_MONITOR_STATIC_DIR"):
        p = Path(os.environ["UBUNTU_MONITOR_STATIC_DIR"])
        if p.is_dir() and (p / "index.html").is_file():
            return p
    if getattr(sys, "frozen", False):
        p = Path(sys.executable).parent / "web" / "dist"
        if p.is_dir() and (p / "index.html").is_file():
            return p
    p = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
    if p.is_dir() and (p / "index.html").is_file():
        return p
    return None


_static = _dashboard_static_dir()
if _static:
    app.mount("/", StaticFiles(directory=str(_static), html=True), name="dashboard")
