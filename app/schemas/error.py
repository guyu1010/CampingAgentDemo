from pydantic import BaseModel

class ErrorResponse(BaseModel):
    """統一錯誤回應格式"""
    status_code: int
    detail: str