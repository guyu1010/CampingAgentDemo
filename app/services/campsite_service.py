from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.campsite import Campsite
from app.models.district import District, CountyAlias
from app.schemas.campsite import CampsiteResponse
from fastapi import HTTPException
import math

class CampsiteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_campsite(self):
        result = await self.db.execute(select(Campsite))
        return result.scalars().all()

    # 根據 county 篩選露營地
    async def get_campsite_by_county(self, county: str):
        result = await self.db.execute(select(Campsite).where(Campsite.county == county))
        return result.scalars().all()

    # 根據 district 篩選露營地
    async def get_campsite_by_district(self, district: str):
            result = await self.db.execute(select(Campsite).where(Campsite.district == district))
            return result.scalars().all()

    # 根據指定位置取最近露營地清單
    async def get_near_campsite(self, county: str, district: str | None = None):

        county = await self.resolve_county(county)

        # 取起點座標
        (lng, lat) = await self.get_location_coordinate(county, district)

        # 取全部露營地
        campsite_all = await self.get_campsite()

        distances = []

        # 計算起點到各點距離
        for item_campsite in campsite_all:
            km = self.calculate_distance_km(lng, lat, item_campsite.lng, item_campsite.lat)
            t = (round(km, 2), item_campsite)
            distances.append(t)

        distances.sort(key=lambda x: x[0])
        top5 = distances[:5]

        result = []
        for i in top5:
            obj = CampsiteResponse.model_validate(i[1]).model_dump()
            obj["distance_km"] = i[0]
            result.append(obj)

        return result

    # 根據 county 及 district 回傳經緯度
    async def get_location_coordinate(self, county: str, district: str | None = None):

        if district is None:
            result = await self.db.execute(select(District).where(District.county == county, District.is_default.is_(True)))
        else:
            result = await self.db.execute(select(District).where(District.county == county, District.district == district))

        data = result.scalar_one_or_none()

        if data is None:
            raise HTTPException(404, "找不到該地點")

        return (data.lng, data.lat)

    # 計算兩點距離
    @staticmethod
    def calculate_distance_km(lon1: float, lat1: float, lon2: float, lat2: float):

        lon1, lat1, lon2, lat2 = map(math.radians, (lon1, lat1, lon2, lat2))

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        # 地球平均半徑（公里)
        r = 6371.0

        return c * r

    async def resolve_county(self, county: str):
        result = await self.db.execute(select(CountyAlias).where(CountyAlias.alias == county))
        resolved = result.scalar_one_or_none()

        if resolved is None:
            return county

        return resolved.county
