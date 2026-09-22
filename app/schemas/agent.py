from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str | None = None
    question: str = Field(..., min_length=1, max_length=500, description="使用者的提問")

class ChatResponse(BaseModel):
    session_id: str
    answer: str
