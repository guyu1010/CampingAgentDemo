from fastapi import HTTPException, status
from app.core.config import settings
from openai import AsyncOpenAI, APIError, APITimeoutError
from app.services.campsite_service import CampsiteService
from app.services.weather_service import WeatherService
from app.schemas.agent import ChatResponse
import json
import uuid

SYSTEM_PROMPT = """- 身份與範圍:你是台灣露營助理,只回答露營相關問題。
- 縣市名稱規則:一律用「臺」而非「台」,呼叫工具前先轉成正式名稱。
- 回答風格:繁體中文、簡潔、列出全部 5 個結果。
- 模糊情況怎麼辦:例如使用者說「嘉義」時,先反問是縣還是市。
- 工具使用策略:問天氣時,要先取得座標。"""

tools = [
    {
        "type": "function",
        "name": "find_nearest_campsites",
        "description": "查詢指定地點最近的5個露營地資訊。",
        "parameters": {
            "type": "object",
            "properties": {
                "county": {
                    "type": "string",
                    "description": "臺灣的縣市，例如臺中市。",
                },
                "district": {
                    "type": ["string", "null"],
                    "description": "臺灣的鄉鎮市區，例如大里區。沒有指定鄉鎮時填 null",
                },
            },
            "required": ["county","district"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_weather",
        "description": "使用者問天氣、要不要帶雨具、適不適合露營時。座標可以取自露營地查詢結果的 lat、lng",
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "緯度",
                },
                "lng": {
                    "type": "number",
                    "description": "經度",
                },
            },
            "required": ["lat","lng"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]

OPENAI_ERROR_MAP = {
    400: (status.HTTP_500_INTERNAL_SERVER_ERROR, "請求內容無效（可能超過 Token 限制）。"),
    401: (status.HTTP_500_INTERNAL_SERVER_ERROR, "系統認證失敗，請聯絡管理員。"),
    429: (status.HTTP_429_TOO_MANY_REQUESTS, "服務太過繁忙或額度已滿，請稍後再試。"),
}

MAX_TURNS = 3
session = {}

class AgentService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def sessionManage(session_id: str, chat_history: list):
        user_positions = []
        for i in range(len(chat_history)):
            if isinstance(chat_history[i], dict) and chat_history[i].get("role") == "user":
                user_positions.append(i)

        if len(user_positions) > MAX_TURNS:
            start = user_positions[-MAX_TURNS]
            chat_history = chat_history[start:]

        session[session_id] = chat_history

    async def chat(self, session_id: str | None, question: str):
        chat_history = list(session.get(session_id, []))

        if session_id is None or session_id not in session:
            session_id = str(uuid.uuid4())

        message = {
            "role": "user",
            "content": question
        }
        chat_history.append(message)
        # self.sessionManage(session_id, chat_history)

        client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=30)

        for _ in range(5):
            try:
                response = await client.responses.create(
                    model=settings.openai_model,
                    input=chat_history,
                    tools=tools,
                    instructions = SYSTEM_PROMPT)
            except APITimeoutError as e:
                print(repr(e))
                raise HTTPException(status_code=504, detail="呼叫逾時") from e

            except APIError as e:
                print(repr(e))

                http_status, detail = OPENAI_ERROR_MAP.get(getattr(e, "status_code", None), (status.HTTP_502_BAD_GATEWAY, "AI 服務回應異常。"))
                raise HTTPException(status_code=http_status, detail=detail) from e

            except Exception as e:
                print(repr(e))
                raise HTTPException(status_code=500, detail="系統發生內部錯誤。") from e

            tool_calls = []

            for item in response.output:
                if item.type == "function_call":
                    tool = {
                        "data": item.arguments,
                        "name": item.name,
                        "call_id":item.call_id
                    }
                    tool_calls.append(tool)

            chat_history += response.output
            # self.sessionManage(session_id, chat_history)

            if len(tool_calls) == 0:
                self.sessionManage(session_id, chat_history)
                return ChatResponse(session_id=session_id, answer=response.output_text)

            for tool_item in tool_calls:
                try:
                    if tool_item["name"] == "find_nearest_campsites":
                        args = json.loads(tool_item["data"])
                        service = CampsiteService(self.db)
                        result = await service.get_near_campsite(args["county"], args["district"])
                    elif tool_item["name"] == "get_weather":
                        args = json.loads(tool_item["data"])
                        weather = await WeatherService().get_weather(args["lat"], args["lng"])
                        result = weather.model_dump()
                    else:
                        result = "未知的工具"
                except HTTPException as e:
                        result = {"error": e.detail}
                        print(repr(e))
                except Exception as e:
                        result = {"error": "工具執行失敗"}
                        print(repr(e))

                chat_history.append({
                    "type": "function_call_output",
                    "call_id": tool_item["call_id"],
                    "output": json.dumps(result, ensure_ascii=False),
                })

        return ChatResponse(session_id=session_id, answer="找不到答案")
