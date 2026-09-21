from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class District(Base):
    __tablename__ = "district"
    __table_args__ = (UniqueConstraint("county", "district"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    county: Mapped[str]
    district: Mapped[str]
    lng: Mapped[float]
    lat: Mapped[float]
    is_default: Mapped[bool]  # 該縣市人口最多的鄉鎮市區,只說縣市時以此為基準

class CountyAlias(Base):
    __tablename__ = "county_alias"

    alias: Mapped[str] = mapped_column(primary_key=True)
    county: Mapped[str]
