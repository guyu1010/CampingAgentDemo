import pytest
from sqlalchemy import select
from app.models.district import CountyAlias
from app.services import agent
from app.services.agent import AgentService
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_db_session_works(db_session):
    result = await db_session.execute(select(CountyAlias))
    rows = result.scalars().all()
    assert rows == []

def test_clean_session():
    agent._session_store.clear()

    chat_history = []
    now = datetime.now()

    agent._session_store["fresh"] = (chat_history, now)
    agent._session_store["23h59m"] = (chat_history, now - timedelta(hours=23, minutes=59))
    agent._session_store["24h00m01s"] = (chat_history, now - timedelta(hours=24, seconds=1))
    agent._session_store["25h"] = (chat_history, now - timedelta(hours=25))

    AgentService.clean_session()

    assert "fresh" in agent._session_store
    assert "23h59m" in agent._session_store
    assert "24h00m01s" not in agent._session_store
    assert "25h" not in agent._session_store

def make_tool_call_response(name, arguments, call_id="call_1"):
    return SimpleNamespace(
        output=[SimpleNamespace(
            type="function_call",
            name=name,
            arguments=arguments,
            call_id=call_id
        )],
        output_text=""
    )

def make_final_response(text):
    return SimpleNamespace(output=[], output_text=text)

@pytest.mark.asyncio
async def test_chat_stream(db_session, monkeypatch):

    fake_client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(side_effect=[
        make_tool_call_response("get_weather", '{"lat": 24.1, "lng": 120.6}'),
        make_final_response("今天天氣晴朗，適合露營")
    ])))

    monkeypatch.setattr(
        agent.WeatherService, "get_weather",
        AsyncMock(return_value=SimpleNamespace(model_dump=lambda: {"temp": 28}))
    )

    service = AgentService(db_session, fake_client)
    events = [event async for event in service.chat_stream(None, "臺中天氣如何")]

    assert events[0] == {"type": "tool_call", "tool": "get_weather"}
    assert events[-1]["type"] == "answer"
    assert events[-1]["answer"] == "今天天氣晴朗，適合露營"
    assert fake_client.responses.create.await_count == 2
