import pytest
from app.services.campsite_service import CampsiteService
from sqlalchemy import select
from app.models.district import CountyAlias
from app.services import agent
from app.services.agent import AgentService
from datetime import datetime, timedelta

def test_calculate_distance_km():
    taipel = (121.56, 25.03)
    taichung = (120.67, 24.15)
    result = CampsiteService.calculate_distance_km(taipel[0], taipel[1], taichung[0], taichung[1])

    assert result == pytest.approx(132.9, abs=1)

@pytest.mark.asyncio
async def test_db_session_works(db_session):
    result = await db_session.execute(select(CountyAlias))
    rows = result.scalars().all()
    assert rows == []

@pytest.mark.asyncio
async def test_resolve_county_with_alias(db_session):

    alias = CountyAlias(alias="台北", county="臺北市")
    db_session.add(alias)
    await db_session.commit()

    service = CampsiteService(db_session)
    res = await service.resolve_county("台北")

    assert res == "臺北市"

@pytest.mark.asyncio
async def test_resolve_county_fallback(db_session):
    service = CampsiteService(db_session)
    result = await service.resolve_county("新竹")
    assert result == "新竹"

def test_clean_session():
    agent.session.clear()

    chat_history = []
    now = datetime.now()

    agent.session["fresh"] = (chat_history, now)
    agent.session["23h59m"] = (chat_history, now - timedelta(hours=23, minutes=59))
    agent.session["24h00m01s"] = (chat_history, now - timedelta(hours=24, seconds=1))
    agent.session["25h"] = (chat_history, now - timedelta(hours=25))

    AgentService.clean_session()

    assert "fresh" in agent.session
    assert "23h59m" in agent.session
    assert "24h00m01s" not in agent.session
    assert "25h" not in agent.session
