import asyncio
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import delete

from app.db.database import AsyncSessionLocal, Base, engine
from app.models.district import CountyAlias, District

JSON_PATH = Path(__file__).resolve().parent.parent / "docs" / "position.json"

EXCLUDED = {"高雄市東沙群島", "高雄市南沙群島"}

DEFAULT_DISTRICT = {
    "臺北市": "大安區", "新北市": "板橋區", "桃園市": "桃園區",
    "臺中市": "北屯區", "臺南市": "永康區", "高雄市": "鳳山區",
    "基隆市": "安樂區", "新竹市": "東區", "嘉義市": "西區",
    "新竹縣": "竹北市", "苗栗縣": "頭份市", "彰化縣": "彰化市",
    "南投縣": "草屯鎮", "雲林縣": "斗六市", "嘉義縣": "民雄鄉",
    "屏東縣": "屏東市", "宜蘭縣": "宜蘭市", "花蓮縣": "花蓮市",
    "臺東縣": "臺東市", "澎湖縣": "馬公市", "金門縣": "金城鎮",
    "連江縣": "南竿鄉",
}


def build_districts() -> list[District]:
    """讀取 JSON 檔,轉成 District 物件清單。"""
    with open(JSON_PATH, encoding="utf-8") as f:
        raw_list = json.load(f)

    districts = []
    for item in raw_list:
        name = item["name"]
        if name in EXCLUDED:
            continue

        county = name[:3]    # 縣市名固定3個字
        district = name[3:]  # 剩下的是鄉鎮市區

        districts.append(District(
            county=county,
            district=district,
            lng=item["location"]["lng"],
            lat=item["location"]["lat"],
            is_default=DEFAULT_DISTRICT.get(county) == district,
        ))

    check_one_default_per_county(districts)
    return districts


def check_one_default_per_county(districts: list[District]):
    """確認每個縣市都剛好有一個預設鄉鎮市區"""
    default_counts = Counter(d.county for d in districts if d.is_default)
    assert len(default_counts) == 22, f"應該有 22 個縣市有預設鄉鎮市區,實際有 {len(default_counts)} 個"
    for county, count in default_counts.items():
        assert count == 1, f"{county} 有 {count} 個預設鄉鎮市區,應該只能有 1 個"


def build_aliases(counties: list[str]) -> list[CountyAlias]:
    """幫每個縣市建立常見別名，例如「北市」能對應到「臺北市」"""
    alias_to_county = {}

    def add_alias(alias: str, county: str):
        alias_to_county[alias] = county
        alias_to_county[alias.replace("臺", "台")] = county

    # 新竹、嘉義同時有縣跟市，這種縣市不建簡稱
    short_name_counts = Counter(county[:-1] for county in counties)

    for county in counties:
        add_alias(county, county)

        short_name = county[:-1]
        if short_name_counts[short_name] == 1:
            add_alias(short_name, county)

    aliases = [CountyAlias(alias=alias, county=county) for alias, county in alias_to_county.items()]
    aliases.sort(key=lambda a: a.alias)
    return aliases


async def main():
    districts = build_districts()
    aliases = build_aliases(sorted({d.county for d in districts}))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await session.execute(delete(District))
        await session.execute(delete(CountyAlias))
        session.add_all(districts)
        session.add_all(aliases)
        await session.commit()

    print(f"已匯入 {len(districts)} 筆鄉鎮市區、{len(aliases)} 筆縣市別名")


if __name__ == "__main__":
    asyncio.run(main())
