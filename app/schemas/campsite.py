from pydantic import BaseModel, Field

class CampsiteBase(BaseModel):
    id: int
    name: str
    county: str
    district: str
    lng: float
    lat: float
    address: str
    phone: str
    website: str

class CampsiteResponse(CampsiteBase):
    pass

    model_config = {
        "from_attributes": True  # 讓它能直接讀 SQLAlchemy物件轉成Pydantic
    }

class CampsiteListResponse(CampsiteResponse):
    distance_km: float