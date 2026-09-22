import httpx
from fastapi import HTTPException

from app.schemas.weather import WeatherResponse

# 定義 WMO 天氣代碼與中文描述的對應字典
WMO_WEATHER_MAP = {
    0: "晴朗",
    1: "主要晴朗",
    2: "晴時多雲",
    3: "陰天",
    45: "有霧",
    48: "霧淞霧",
    51: "輕微毛毛雨",
    53: "中度毛毛雨",
    55: "重度毛毛雨",
    56: "輕微凍毛毛雨",
    57: "重度凍毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "輕微凍雨",
    67: "重度凍雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "微弱陣雨",
    81: "中等陣雨",
    82: "強烈陣雨",
    85: "微弱陣雪",
    86: "強烈陣雪",
    95: "雷陣雨",
    96: "雷陣雨伴隨輕微冰雹",
    99: "雷陣雨伴隨嚴重冰雹"
}

class WeatherService:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    async def get_weather(self, lat: float, lng: float):
        params = {
            "latitude": lat,
            "longitude": lng,
            "current": "temperature_2m,precipitation,weather_code",
            "timezone": "Asia/Taipei"
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="天氣服務回應逾時")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"天氣服務回傳錯誤 ({e.response.status_code})")

        current = data["current"]

        return WeatherResponse(
            time=current["time"],
            temperature=current["temperature_2m"],
            precipitation=current["precipitation"],
            weather_code=current["weather_code"],
            description=WMO_WEATHER_MAP.get(current["weather_code"], "未知天氣")
        )
