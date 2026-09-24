import pytest
from app.services.campsite_service import CampsiteService
from app.models.district import CountyAlias

def test_calculate_distance_km():
    taipel = (121.56, 25.03)
    taichung = (120.67, 24.15)
    result = CampsiteService.calculate_distance_km(taipel[0], taipel[1], taichung[0], taichung[1])

    assert result == pytest.approx(132.9, abs=1)

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
