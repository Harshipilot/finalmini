import requests
import os
import plotly.graph_objects as go
import plotly.express as px

# Load API Key
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# AQI Labels + Color Codes
AQI_LABELS = {
    1: ("Good", "#2ECC71"),
    2: ("Fair", "#A3E4D7"),
    3: ("Moderate", "#F4D03F"),
    4: ("Poor", "#E67E22"),
    5: ("Very Poor", "#E74C3C")
}

def build_aqi_gauge(aqi, label, color):
    """Plotly AQI Gauge Chart"""
    return go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=aqi,
            title={'text': f"AQI — {label}"},
            gauge={
                "axis": {"range": [0, 5]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 1], "color": "#2ECC71"},
                    {"range": [1, 2], "color": "#A3E4D7"},
                    {"range": [2, 3], "color": "#F4D03F"},
                    {"range": [3, 4], "color": "#E67E22"},
                    {"range": [4, 5], "color": "#E74C3C"},
                ]
            }
        )
    )


def build_pollutant_bar(components):
    """Bar Chart for Pollutants"""
    data = {
        "Pollutant": list(components.keys()),
        "Value (µg/m³)": list(components.values())
    }
    fig = px.bar(
        data,
        x="Pollutant",
        y="Value (µg/m³)",
        title="Pollution Level Breakdown",
        text_auto=True
    )
    fig.update_layout(showlegend=False)
    return fig


def build_pollutant_pie(components):
    """Pie chart of pollutant composition"""
    labels = list(components.keys())
    values = list(components.values())

    fig = px.pie(
        names=labels,
        values=values,
        title="Pollutant Composition",
        hole=0.4
    )
    return fig


def get_air_quality(city):
    """Fetch AQI + return visual charts + pollutant data"""

    try:
        # Step 1 — Get city coordinates
        geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        geo_params = {"q": city, "limit": 1, "appid": OPENWEATHER_API_KEY}
        geo_res = requests.get(geo_url, params=geo_params).json()

        if not geo_res:
            return {"error": "City not found"}

        lat = geo_res[0]["lat"]
        lon = geo_res[0]["lon"]

        # Step 2 — Fetch air pollution data
        air_url = "http://api.openweathermap.org/data/2.5/air_pollution"
        air_params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY}
        air_res = requests.get(air_url, params=air_params).json()

        if "list" not in air_res:
            return {"error": "No air quality data available"}

        air_info = air_res["list"][0]

        # AQI (1–5)
        aqi = air_info["main"]["aqi"]
        label, color = AQI_LABELS.get(aqi, ("Unknown", "#7F8C8D"))

        components = air_info["components"]  # PM2.5, CO, NO2, etc.

        # Build charts
        aqi_gauge = build_aqi_gauge(aqi, label, color)
        pollutant_bar = build_pollutant_bar(components)
        pollutant_pie = build_pollutant_pie(components)

        return {
            "city": city,
            "lat": lat,
            "lon": lon,
            "aqi": aqi,
            "aqi_label": label,
            "aqi_color": color,
            "components": components,
            "timestamp": air_info.get("dt"),
            "aqi_gauge": aqi_gauge,
            "pollutant_bar": pollutant_bar,
            "pollutant_pie": pollutant_pie,
            "error": None
        }

    except Exception as e:
        return {"error": str(e)}
