from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.agent import ChatRequest, ChatResponse
from app.services.agent import AgentService, AsyncOpenAI, get_openai_client

router = APIRouter(prefix="/api/chat", tags=["Agent"])

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db), client: AsyncOpenAI = Depends(get_openai_client)):
    return await AgentService(db, client).chat(request.session_id, request.question)
