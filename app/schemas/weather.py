from pydantic import BaseModel

class WeatherResponse(BaseModel):
    time: str
    temperature: float      # °C
    precipitation: float    # mm
    weather_code: int
    description: str

