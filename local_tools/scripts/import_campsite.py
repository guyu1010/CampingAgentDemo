import asyncio
import csv
from pathlib import Path

from sqlalchemy import delete

from app.db.database import AsyncSessionLocal, Base, engine
from app.models.campsite import Campsite

CSV_PATH = Path(__file__).resolve().parent.parent / "docs" / "campsite.csv"


def parse_row(row: dict) -> Campsite | None:
    lng = row["經度"].strip()
    lat = row["緯度"].strip()
    if not lng or not lat: # 缺經緯度跳過
        return None

    phone = row["電話"].strip()
    if not phone:
        phone = row["手機"].strip()  # 電話沒有用手機號碼

    return Campsite(
        name=row["露營場名稱"].strip(),
        county=row["縣市別"].strip(),
        district=row["鄉/鎮/市/區"].strip(),
        lng=float(lng),
        lat=float(lat),
        address=row["地址"].strip(),
        phone=phone,
        website=row["網站"].strip(),
    )


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    campsites = []
    skipped_names = []

    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            campsite = parse_row(row)
            if campsite is None:
                skipped_names.append(row["露營場名稱"])
            else:
                campsites.append(campsite)

    async with AsyncSessionLocal() as session:
        await session.execute(delete(Campsite))
        session.add_all(campsites)
        await session.commit()

    print(f"已匯入 {len(campsites)} 筆,略過 {len(skipped_names)} 筆")


if __name__ == "__main__":
    asyncio.run(main())
