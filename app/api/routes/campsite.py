from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.campsite_service import CampsiteService
from app.schemas.campsite import CampsiteResponse, CampsiteListResponse

router = APIRouter(prefix="/api/campsite", tags=["Campsite"])

@router.get("/", response_model=list[CampsiteResponse])
async def get_campsite(db: AsyncSession = Depends(get_db)):
    return await CampsiteService(db).get_campsite()

@router.get("/county/{county}", response_model=list[CampsiteResponse])
async def get_campsite_by_county(county: str, db: AsyncSession = Depends(get_db)):
    return await CampsiteService(db).get_campsite_by_county(county)

@router.get("/district/{district}", response_model=list[CampsiteResponse])
async def get_campsite_by_district(district: str, db: AsyncSession = Depends(get_db)):
    return await CampsiteService(db).get_campsite_by_district(district)

@router.get("/near", response_model=list[CampsiteListResponse])
async def get_near_campsite(county: str, district: str | None = None, db: AsyncSession = Depends(get_db)):
    return await CampsiteService(db).get_near_campsite(county, district)

