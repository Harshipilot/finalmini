from pytrends.request import TrendReq
import requests
import os

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

CUSTOM_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/113.0.0.0 Safari/537.36"
)


def fetch_places(query):
    """Fetch locations using Google Places API."""
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": GOOGLE_PLACES_API_KEY}

    r = requests.get(url, params=params)
    data = r.json()

    status = data.get("status")
    error_message = data.get("error_message")

    # If error
    if status != "OK":
        return [], status, error_message

    results = data.get("results", [])
    places = []

    for place in results[:10]:
        try:
            place_id = place.get("place_id")
            name = place.get("name", "Unknown")
            address = place.get("formatted_address", "No address")
            rating = place.get("rating", "N/A")

            lat = place["geometry"]["location"]["lat"]
            lng = place["geometry"]["location"]["lng"]
        except:
            continue

        # ---- Fetch More Details ----
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "key": GOOGLE_PLACES_API_KEY,
            "fields": "formatted_phone_number,website,opening_hours"
        }

        dr = requests.get(details_url, params=details_params)
        details = dr.json().get("result", {})

        places.append({
            "name": name,
            "address": address,
            "rating": rating,
            "lat": lat,
            "lng": lng,
            "website": details.get("website", "Not available"),
            "phone": details.get("formatted_phone_number", "N/A"),
            "opening_hours": details.get("opening_hours", {}).get("weekday_text", [])
        })

    return places, status, error_message


def get_recommendations(city):

    # -----------------------------
    # GOOGLE TRENDS
    # -----------------------------
    pytrends = TrendReq(
        hl="en-US",
        tz=360,
        requests_args={"headers": {"User-Agent": CUSTOM_USER_AGENT}}
    )

    keyword = f"tourist places in {city}"
    trends = []

    try:
        pytrends.build_payload([keyword], timeframe="now 7-d")
        interest = pytrends.interest_over_time()

        if not interest.empty:
            for ts, row in interest.iterrows():
                trends.append({
                    "date": str(ts.date()),
                    "interest": int(row.get(keyword, 0))
                })
    except:
        trends.append({"error": "Google Trends request failed"})

    # -----------------------------
    # GOOGLE PLACES: MULTI-QUERY FALLBACK
    # -----------------------------
    queries = [
        f"top attractions in {city}",
        f"tourist places in {city}",
        f"best places to visit in {city}",
        f"{city} sightseeing",
        f"{city} tourist hotspots"
    ]

    all_places = []
    for q in queries:
        places, status, err = fetch_places(q)

        if places:  # Found something
            all_places = places
            break

    # If still empty
    if not all_places:
        all_places = [{
            "error": f"No tourist data found for {city}. API status={status}, error={err}"
        }]

    # Remove duplicates (same lat/lng)
    unique = {}
    for p in all_places:
        key = (p.get("lat"), p.get("lng"))
        if key not in unique:
            unique[key] = p

    return {
        "trends": trends,
        "places": list(unique.values())
    }
