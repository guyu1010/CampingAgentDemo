import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import agent, campsite, weather
from app.core.config import settings
from app.db.database import Base, engine
from app.services.agent import AgentService


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # 啟動時自動建表

    asyncio.create_task(AgentService.run_cleanup_scheduler()) # 啟動自動執行清理session排程
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

@app.exception_handler(HTTPException)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )

app.include_router(campsite.router)
app.include_router(weather.router)
app.include_router(agent.router)

app.mount("/web", StaticFiles(directory="web", html=True), name="web")
