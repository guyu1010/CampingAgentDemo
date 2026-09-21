from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class Campsite(Base):
    __tablename__ = "campsite"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    county: Mapped[str]
    district: Mapped[str]
    lng: Mapped[float]
    lat: Mapped[float]
    address: Mapped[str]
    phone: Mapped[str]
    website: Mapped[str]