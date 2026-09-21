from fastapi import FastAPI, HTTPException
from app.api.routes import campsite, weather, agent
from app.core.config import settings
from app.db.database import engine, Base
import app.models.district
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from app.schemas.error import ErrorResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # 啟動時自動建表
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

@app.get("/")
def root():
    return {"message": "server run"}

