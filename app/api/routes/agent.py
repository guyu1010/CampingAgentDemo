from fastapi import APIRouter, Depends
from app.db.database import get_db
from app.services.agent import AgentService
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.agent import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["Agent"])

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    return await AgentService(db).chat(request.session_id, request.question)
