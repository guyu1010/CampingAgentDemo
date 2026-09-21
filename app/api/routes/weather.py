from typing import Annotated
from fastapi import APIRouter, Query
from app.services.weather_service import WeatherService
from app.schemas.weather import WeatherResponse

router = APIRouter(prefix="/api/weather", tags=["Weather"])

@router.get("/", response_model=WeatherResponse)
async def get_weather(lat: Annotated[float, Query(ge=-90, le=90, description="緯度")], lng: Annotated[float, Query(ge=-180, le=180, description="經度")]):
    return await WeatherService().get_weather(lat, lng)

