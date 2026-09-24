import pytest
from sqlalchemy import select
from app.models.district import CountyAlias
from app.services import agent
from app.services.agent import AgentService
from datetime import datetime, timedelta

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
