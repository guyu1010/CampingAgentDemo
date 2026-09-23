from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.schemas.agent import ChatRequest, ChatResponse
from app.services.agent import AgentService, AsyncOpenAI, get_openai_client

router = APIRouter(prefix="/api/chat", tags=["Agent"])

@router.get("/status")
async def status():
    return {"enabled": settings.ai_enabled}

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db), client: AsyncOpenAI = Depends(get_openai_client)):
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI展示功能未開放")
    return await AgentService(db, client).chat(request.session_id, request.question)
