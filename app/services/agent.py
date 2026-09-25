import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from openai import APIError, APITimeoutError, AsyncOpenAI

from app.core.config import settings
from app.schemas.agent import ChatResponse
from app.services.campsite_service import CampsiteService
from app.services.knowledge_service import KnowledgeService
from app.services.weather_service import WeatherService


SYSTEM_PROMPT = """- 身份與範圍:你是台灣露營助理,只回答露營相關問題。
- 縣市名稱規則:一律用「臺」而非「台」,呼叫工具前先轉成正式名稱。
- 回答風格:繁體中文、簡潔、預設列出 5 個結果，但如果使用者指定數量時，以使用者需求為準。
- 模糊情況怎麼辦:例如使用者說「嘉義」時,先反問是縣還是市。
- 工具使用策略:問天氣時,要先取得座標。使用者問安全注意事項、該不該去、要準備什麼,或查完天氣發現有大雨/高溫/寒冷等可能影響人身安全時，呼叫 search_camping_knowledge。
- search_camping_knowledge 是用語意相似度搜出結果，不保證每段都真的相關，只採用真正回答到問題的段落，不相關的直接忽略，不要為了湊內容硬套用。"""

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
    },
    {
        "type": "function",
        "name": "search_camping_knowledge",
        "description": "使用者問注意事項或者使用天氣工具後，判斷大雨、寒冷、炎熱可能造成人體危害時，可以查詢相關知識",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "使用者想了解的露營安全主題，用簡短的中文描述情境即可，例如：「打雷該怎麼辦」「有蛇出沒怎麼辦」「午後雷陣雨可以露營嗎」。",
                }
            },
            "required": ["query"],
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

MAX_TOOL_CALL_LOOPS = 5
MAX_TURNS = 3
_session_store = {}

client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=30)

logger = logging.getLogger(__name__)

def get_openai_client():
    return client

class AgentService:
    def __init__(self, db, client):
        self.db = db
        self.client = client

    @staticmethod
    def session_manage(session_id: str, chat_history: list, last_active_at: datetime):
        user_positions = []
        for i in range(len(chat_history)):
            if isinstance(chat_history[i], dict) and chat_history[i].get("role") == "user":
                user_positions.append(i)

        if len(user_positions) > MAX_TURNS:
            start = user_positions[-MAX_TURNS]
            chat_history = chat_history[start:]

        _session_store[session_id] = (chat_history, last_active_at)

    @staticmethod
    async def run_cleanup_scheduler():
        while True:
            try:
                AgentService.clean_session()
            except Exception as e:
                logger.error("清理過程中發生錯誤: %r", e)

            await asyncio.sleep(6 * 60 * 60)

    @staticmethod
    def clean_session():
        cutoff_time = datetime.now() - timedelta(hours=24)

        remove = []
        for key, (_, dt) in _session_store.items():
            if dt < cutoff_time:
                remove.append(key)

        # 遍尋刪除所有過期的字典
        for key in remove:
            del _session_store[key]

    async def chat(self, session_id: str | None, question: str):
        chat_history, last_active_at = list(_session_store.get(session_id, ([], None)))

        if session_id is None or session_id not in _session_store:
            session_id = str(uuid.uuid4())
            last_active_at = datetime.now()

        message = {
            "role": "user",
            "content": question
        }
        chat_history.append(message)

        for _ in range(MAX_TOOL_CALL_LOOPS):
            try:
                response = await self.client.responses.create(
                    model=settings.openai_model,
                    input=chat_history,
                    tools=tools,
                    instructions = SYSTEM_PROMPT)
            except APITimeoutError as e:
                logger.error("OpenAI 呼叫逾時: %r", e)
                raise HTTPException(status_code=504, detail="呼叫逾時") from e

            except APIError as e:
                logger.error("OpenAI API 錯誤: %r", e)

                http_status, detail = OPENAI_ERROR_MAP.get(getattr(e, "status_code", None), (status.HTTP_502_BAD_GATEWAY, "AI 服務回應異常。"))
                raise HTTPException(status_code=http_status, detail=detail) from e

            except Exception as e:
                logger.error("系統發生非預期錯誤: %r", e)
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
                self.session_manage(session_id, chat_history, last_active_at)
                return ChatResponse(session_id=session_id, answer=response.output_text)

            for tool_item in tool_calls:
                logger.info("AI呼叫工具： %s, 參數： %s", tool_item["name"], tool_item["data"])
                
                try:
                    if tool_item["name"] == "find_nearest_campsites":
                        args = json.loads(tool_item["data"])
                        service = CampsiteService(self.db)
                        result = await service.get_near_campsite(args["county"], args["district"])
                    elif tool_item["name"] == "get_weather":
                        args = json.loads(tool_item["data"])
                        weather = await WeatherService().get_weather(args["lat"], args["lng"])
                        result = weather.model_dump()
                    elif tool_item["name"] == "search_camping_knowledge":
                        args = json.loads(tool_item["data"])
                        result = await KnowledgeService(self.client).search(args["query"])
                    else:
                        result = "未知的工具"
                except HTTPException as e:
                        result = {"error": e.detail}
                        logger.error("工具執行時發生 HTTPException: %r", e)
                except Exception as e:
                        result = {"error": "工具執行失敗"}
                        logger.error("工具執行失敗: %r", e)

                chat_history.append({
                    "type": "function_call_output",
                    "call_id": tool_item["call_id"],
                    "output": json.dumps(result, ensure_ascii=False),
                })

        return ChatResponse(session_id=session_id, answer="找不到答案")

    async def chat_stream(self, session_id: str | None, question: str):
        chat_history, last_active_at = list(_session_store.get(session_id, ([], None)))

        if session_id is None or session_id not in _session_store:
            session_id = str(uuid.uuid4())
            last_active_at = datetime.now()

        message = {
            "role": "user",
            "content": question
        }
        chat_history.append(message)

        for _ in range(MAX_TOOL_CALL_LOOPS):
            try:
                response = await self.client.responses.create(
                    model=settings.openai_model,
                    input=chat_history,
                    tools=tools,
                    instructions = SYSTEM_PROMPT)
            except APITimeoutError as e:
                logger.error("OpenAI 呼叫逾時: %r", e)
                yield {"type": "error", "detail": "呼叫逾時"}
                return

            except APIError as e:
                logger.error("OpenAI API 錯誤: %r", e)

                http_status, detail = OPENAI_ERROR_MAP.get(getattr(e, "status_code", None), (status.HTTP_502_BAD_GATEWAY, "AI 服務回應異常。"))
                yield {"type": "error", "detail": detail}
                return

            except Exception as e:
                logger.error("系統發生非預期錯誤: %r", e)
                yield {"type": "error", "detail": "系統發生內部錯誤。"}
                return

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

            if len(tool_calls) == 0:
                self.session_manage(session_id, chat_history, last_active_at)
                yield {"type": "answer", "session_id": session_id, "answer": response.output_text}
                return

            for tool_item in tool_calls:

                logger.info("AI呼叫工具： %s, 參數： %s", tool_item["name"], tool_item["data"])

                yield {"type": "tool_call", "tool": tool_item["name"]}

                try:
                    if tool_item["name"] == "find_nearest_campsites":
                        args = json.loads(tool_item["data"])
                        service = CampsiteService(self.db)
                        result = await service.get_near_campsite(args["county"], args["district"])
                    elif tool_item["name"] == "get_weather":
                        args = json.loads(tool_item["data"])
                        weather = await WeatherService().get_weather(args["lat"], args["lng"])
                        result = weather.model_dump()
                    elif tool_item["name"] == "search_camping_knowledge":
                        args = json.loads(tool_item["data"])
                        result = await KnowledgeService(self.client).search(args["query"])
                    else:
                        result = "未知的工具"
                except HTTPException as e:
                        result = {"error": e.detail}
                        logger.error("工具執行時發生 HTTPException: %r", e)
                except Exception as e:
                        result = {"error": "工具執行失敗"}
                        logger.error("工具執行失敗: %r", e)

                chat_history.append({
                    "type": "function_call_output",
                    "call_id": tool_item["call_id"],
                    "output": json.dumps(result, ensure_ascii=False),
                })

        yield {"type": "answer", "session_id": session_id, "answer": "找不到答案"}
        return
