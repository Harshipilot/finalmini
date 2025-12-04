import os
import requests
from dotenv import load_dotenv

load_dotenv()

OWM_API = os.getenv("OPENWEATHER_API_KEY")
VC_API = os.getenv("VISUALCROSSING_API_KEY")

# Weather icon base URL
ICON_BASE = "https://openweathermap.org/img/wn/"


def get_current_weather(city_name, lat, lon):
    """Fetch detailed current weather with extra dynamic data."""
    
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&units=metric&appid={OWM_API}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        return {"error": "Failed to fetch current weather"}

    data = response.json()
    
    weather = data["weather"][0]
    main = data["main"]
    wind = data.get("wind", {})
    sys = data.get("sys", {})

    # Compute heat index manually
    temp = main["temp"]
    humidity = main["humidity"]
    heat_index = round(temp + humidity * 0.05, 1)
    
    # Comfort Level
    comfort = "Comfortable"
    if heat_index > 32:
        comfort = "Hot / Discomfort"
    elif heat_index < 10:
        comfort = "Cold / Uncomfortable"

    return {
        "city": city_name,
        "temperature": temp,
        "feels_like": main["feels_like"],
        "humidity": humidity,
        "pressure": main["pressure"],
        "wind_speed": wind.get("speed", 0),
        "wind_deg": wind.get("deg", 0),
        "visibility_km": round(data.get("visibility", 0) / 1000, 1),
        "sunrise": sys.get("sunrise"),
        "sunset": sys.get("sunset"),
        "description": weather["description"].title(),
        "icon_code": weather["icon"],
        "icon_url": f"{ICON_BASE}{weather['icon']}@4x.png",
        "heat_index": heat_index,
        "comfort": comfort,
        "clouds": data["clouds"]["all"],
        "error": None,
    }


def get_monthly_weather(city_name):
    """Fetch monthly weather summary with extended dataset."""
    
    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/"
        f"timeline/{city_name}?unitGroup=metric&include=months&key={VC_API}&contentType=json"
    )

    response = requests.get(url)
    if response.status_code != 200:
        return {"error": "Failed to fetch monthly weather"}

    data = response.json()
    months = data.get("months", [])

    output = []
    for m in months:
        output.append({
            "month": m["month"],
            "avg_temp": m.get("temp"),
            "avg_max": m.get("tempmax"),
            "avg_min": m.get("tempmin"),
            "humidity": m.get("humidity"),
            "precip": m.get("precip"),
            "snow": m.get("snow"),
            "wind": m.get("windspeed"),
            "uv_index": m.get("uvindex"),
        })

    return {
        "city": city_name,
        "months": output,
        "error": None,
    }
