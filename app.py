# app.py
import os
import datetime
import base64
import difflib
from urllib.parse import quote_plus
import io

import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import numpy as np

# Map libraries
import folium
from folium.plugins import MarkerCluster

# Utility modules (assumed present in utils/)
from utils.weather import get_current_weather, get_monthly_weather
from utils.tourist import get_recommendations
from utils.city_api import search_cities
from utils.air_quality import get_air_quality
from utils.crime import get_crime_news
from utils.emergency import get_osm_places
from utils.chatbot import search_google
from utils.reviews import (
    init_reviews_db, add_review, get_reviews_for_city,
    get_city_rating_summary, delete_review, process_image, load_image_from_bytes
)

# ---------------------------------------------------
# Page config & optional cache clears
# ---------------------------------------------------
st.set_page_config(page_title="City Pulse", layout="wide")
try:
    # clear caches at start (optional)
    st.cache_data.clear()
    st.cache_resource.clear()
except Exception:
    pass

# ---------------- BACKGROUND SWITCHER ----------------
def set_dynamic_background(image_source: str):
    """Sets Streamlit background using local or remote image."""
    if not image_source:
        return
    try:
        if str(image_source).startswith(("http://", "https://")):
            st.markdown(
                f"""
                <style>
                .stApp {{
                    background: linear-gradient(rgba(0,0,0,0.60), rgba(0,0,0,0.85)),
                        url("{image_source}") !important;
                    background-size: cover !important;
                    background-attachment: fixed !important;
                    background-position: center !important;
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )
        else:
            with open(image_source, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            st.markdown(
                f"""
                <style>
                .stApp {{
                    background: linear-gradient(rgba(0,0,0,0.60), rgba(0,0,0,0.85)),
                        url("data:image/jpeg;base64,{encoded}") !important;
                    background-size: cover !important;
                    background-attachment: fixed !important;
                    background-position: center !important;
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )
    except Exception:
        # don't crash on background errors
        pass

# Local image fallback
CITY_BACKGROUNDS = {
    "mumbai": "backgrounds/mumbai.jpg",
    "delhi": "backgrounds/delhi.jpg",
    "Mangalore": "backgrounds/Mangalore.jpg",
    "bengaluru": "backgrounds/bangalore.jpg",
    "Nagpur" : "backgrounds/Nagpur.jpg",
    "Hyderabad": "backgrounds/Hyderabad.jpg",
    "Kolkata": "backgrounds/Kolkata.jpg",
}

# ---------------- UNSPLASH (optional) ----------------
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_CREDIT = "Unsplash"

@st.cache_data(show_spinner=False)
def fetch_city_image(city: str):
    """Returns a city image from Unsplash, or None if no API key or failure."""
    if not UNSPLASH_ACCESS_KEY:
        return None

    url = (
        "https://api.unsplash.com/search/photos?"
        f"query={quote_plus(city + ' skyline cityscape')}"
        "&orientation=landscape&content_filter=high&per_page=1"
    )
    headers = {
        "Accept-Version": "v1",
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        photo = results[0]
        return {
            "image_url": photo["urls"]["regular"],
            "color": photo.get("color", "#1f2937"),
            "credit": f"{UNSPLASH_CREDIT} — {photo['user'].get('name','')}",
        }
    except Exception:
        return None

# ---------------- 3D Title (embedded) ----------------
three_js_title = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset='utf-8'>
    <style>
      body { margin: 0; overflow: hidden; background: transparent; }
      canvas { width: 100%; height: 100%; }
    </style>
  </head>
  <body>
    <script src='https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'></script>
    <script src='https://threejs.org/examples/js/loaders/FontLoader.js'></script>
    <script src='https://threejs.org/examples/js/geometries/TextGeometry.js'></script>
    <script>
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(60, window.innerWidth/window.innerHeight, 0.1, 1000);
      const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.setSize(window.innerWidth, window.innerHeight);
      document.body.appendChild(renderer.domElement);

      const light = new THREE.PointLight(0xffffff, 1.4);
      light.position.set(10, 20, 20);
      scene.add(light);

      const loader = new THREE.FontLoader();
      loader.load('https://threejs.org/examples/fonts/helvetiker_bold.typeface.json', (font) => {
        const geo = new THREE.TextGeometry('CITY PULSE', {
          font: font,
          size: 3,
          height: 1,
          curveSegments: 12,
        });

        const mat = new THREE.MeshPhongMaterial({ color: 0x00aaff, shininess: 120 });
        const mesh = new THREE.Mesh(geo, mat);
        geo.center();
        scene.add(mesh);

        camera.position.z = 12;

        function animate(){
          requestAnimationFrame(animate);
          mesh.rotation.y += 0.005;
          mesh.rotation.x += 0.002;
          renderer.render(scene, camera);
        }
        animate();
      });
    </script>
  </body>
</html>
"""

def render_3d_title():
    components.html(three_js_title, height=260)

# ---------------- UI CSS ----------------
def inject_cinematic_css():
    st.markdown(
        """
        <style>
        .stApp {
            background-size: cover !important;
            background-attachment: fixed !important;
            background-position: center !important;
        }
        .hero {
            position: relative;
            border-radius: 22px;
            overflow: hidden;
            height: 340px;
            box-shadow: 0 30px 60px rgba(0,0,0,0.55);
        }
        .hero-content {
            position: absolute;
            bottom: 25px;
            left: 30px;
            color: white;
        }
        .glass {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.18);
            padding: 20px;
            border-radius: 16px;
            backdrop-filter: blur(12px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_cinematic_css()

# Apply saved background if present
if st.session_state.get("city_bg"):
    set_dynamic_background(st.session_state["city_bg"])

# Header
render_3d_title()
st.markdown("<h1 style='text-align:center;color:white;margin-top:-20px;'>Explore Your City Like Never Before</h1>", unsafe_allow_html=True)

# ---------------- CITY SEARCH ----------------
city_query = st.text_input("🔍 Type a city name", placeholder="e.g., Bengaluru, Mangalore, Mumbai")

if not city_query:
    st.info("Type a city to begin your cinematic experience ✨")
else:
    typed = city_query.lower().strip()
    matched_key = None
    if typed in CITY_BACKGROUNDS:
        matched_key = typed
    else:
        close = difflib.get_close_matches(typed, CITY_BACKGROUNDS.keys(), n=1, cutoff=0.6)
        if close:
            matched_key = close[0]

    # Background selection
    if matched_key:
        local_path = CITY_BACKGROUNDS.get(matched_key)
        if local_path and os.path.exists(local_path):
            st.session_state.city_bg = local_path
            set_dynamic_background(local_path)
        else:
            img = fetch_city_image(matched_key)
            if img:
                st.session_state.city_bg = img["image_url"]
                set_dynamic_background(img["image_url"])
    else:
        img = fetch_city_image(typed)
        if img:
            st.session_state.city_bg = img["image_url"]
            set_dynamic_background(img["image_url"])

    # Get city lat/lon via helper
    matched = search_cities(city_query) or []
    if isinstance(matched, dict):
        matched = [matched]

    if not matched:
        st.info("No matching city found.")
    else:
        city_labels = [
            c.get("label") or f"{c.get('name','')} ({c.get('lat', '')},{c.get('lon', '')})"
            for c in matched
        ]
        selected_label = st.selectbox("Select a city:", city_labels)
        selected = next(
            (
                c for c in matched
                if (c.get("label") == selected_label or f"{c.get('name','')} ({c.get('lat', '')},{c.get('lon', '')})" == selected_label)
            ),
            matched[0],
        )

        # Normalize selected city data
        city = selected.get("label") or selected.get("name") or city_query
        # support variations of keys lat/lon or lat/lng
        lat = selected.get("lat") or selected.get("latitude") or selected.get("latlng", [None, None])[0]
        lon = selected.get("lon") or selected.get("lng") or selected.get("longitude") or selected.get("latlng", [None, None])[1]

        # Hero
        im = fetch_city_image(city) or {}
        st.markdown(
            f"""
            <div class='hero' style="background-image:url('{im.get('image_url','')}');background-size:cover;">
                <div class='hero-content'>
                    <div style='font-size:14px;opacity:.85;'>CITY PULSE</div>
                    <div style='font-size:34px;font-weight:800;'>{city}</div>
                    <div style='font-size:15px;opacity:.9;'>{datetime.datetime.now().strftime("%b %d, %Y — %I:%M %p")}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if im.get("credit"):
            st.caption(im["credit"])

        # TABS
        tabs = st.tabs([
            "Weather", "Air Quality", "Tourist Info", "Crime News",
            "Emergency Services", "Trends", "CityBot","Maps","Quiz","fun games", "Reviews"
        ])

        # ---------------- WEATHER TAB ----------------
        with tabs[0]:
            st.header(f"Current Weather in {city}")
            try:
                data = get_current_weather(city, lat, lon) or {}
            except Exception as e:
                data = {"error": f"Weather fetch error: {str(e)}"}

            if data.get("error"):
                st.error(data.get("error") or "Failed to load weather data.")
            else:
                colA, colB = st.columns([1, 3])
                with colA:
                    icon_url = data.get("icon_url")
                    if icon_url:
                        st.image(icon_url, width=120)
                with colB:
                    st.markdown(f"### {data.get('description','No description')}")
                    st.markdown(f"<span style='font-size:18px;color:#ccc;'>Comfort Level: <b>{data.get('comfort','N/A')}</b></span>", unsafe_allow_html=True)

                st.markdown("---")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("🌡️ Temperature", f"{data.get('temperature','N/A')}°C")
                c2.metric("🤒 Feels Like", f"{data.get('feels_like','N/A')}°C")
                c3.metric("💧 Humidity", f"{data.get('humidity','N/A')}%")
                c4.metric("🔥 Heat Index", f"{data.get('heat_index','N/A')}°C")

                st.markdown("### Weather Details")
                colX, colY, colZ = st.columns(3)
                with colX:
                    st.write("**Wind Speed:**", f"{data.get('wind_speed','N/A')} m/s")
                    st.write("**Wind Direction:**", f"{data.get('wind_deg','N/A')}°")
                with colY:
                    st.write("**Pressure:**", f"{data.get('pressure','N/A')} hPa")
                    st.write("**Cloud Cover:**", f"{data.get('clouds','N/A')}%")
                with colZ:
                    sunrise_ts = data.get("sunrise")
                    sunset_ts = data.get("sunset")
                    try:
                        sunrise = datetime.datetime.fromtimestamp(sunrise_ts).strftime("%I:%M %p") if sunrise_ts else "N/A"
                        sunset = datetime.datetime.fromtimestamp(sunset_ts).strftime("%I:%M %p") if sunset_ts else "N/A"
                    except Exception:
                        sunrise, sunset = "N/A", "N/A"
                    st.write("**Sunrise:**", sunrise)
                    st.write("**Sunset:**", sunset)

                st.markdown("---")
                st.metric("👁️ Visibility", f"{data.get('visibility_km','N/A')} km")

        # ---------------- AIR QUALITY TAB ----------------
        with tabs[1]:
            st.header(f"Air Quality in {city}")
            aq = {}
            try:
                # prefer lat/lon signature; fallback to city
                try:
                    aq = get_air_quality(lat, lon) or {}
                except TypeError:
                    aq = get_air_quality(city) or {}
            except Exception as e:
                aq = {"error": f"Air quality fetch error: {str(e)}"}

            if aq.get("error"):
                st.error(aq["error"])
            elif not aq:
                st.info("No air quality data available.")
            else:
                aqi_val = aq.get("aqi", "N/A")
                aqi_label = aq.get("aqi_label", "")
                st.subheader(f"AQI: {aqi_val} {('- ' + aqi_label) if aqi_label else ''}")

                # show components if available
                components_dict = aq.get("components") or {}
                if components_dict:
                    comp_df = pd.DataFrame(list(components_dict.items()), columns=["Pollutant", "Value (µg/m³)"])
                    st.dataframe(comp_df, use_container_width=True)

                # show provided charts if available (plotly)
                if aq.get("aqi_gauge") is not None:
                    try:
                        st.plotly_chart(aq["aqi_gauge"], use_container_width=True)
                    except Exception:
                        pass
                if aq.get("pollutant_bar") is not None:
                    try:
                        st.plotly_chart(aq["pollutant_bar"], use_container_width=True)
                    except Exception:
                        pass
                if aq.get("pollutant_pie") is not None:
                    try:
                        st.plotly_chart(aq["pollutant_pie"], use_container_width=True)
                    except Exception:
                        pass

        # ---------------- TOURIST INFO TAB (Folium map + list) ----------------
        with tabs[2]:
            st.header("🧭 Tourist Information")

            # fetch tourist data (and optional trends) into rec
            rec = {}
            try:
                rec = get_recommendations(city) or {}
            except Exception as e:
                rec = {"error": f"Tourist fetch failed: {str(e)}"}

            places = rec.get("places") if isinstance(rec, dict) else []

            if rec.get("error"):
                st.error(f"No tourist data available for {city}.\n\nAPI Message: {rec.get('error')}")
            elif not places:
                st.info(f"No popular places returned for {city}.")
            else:
                st.subheader(f"Popular Places in {city}")
                # Show list and small map preview for each place
                for place in places:
                    # allow flexible keys
                    pname = place.get("name") or place.get("title") or "Unnamed"
                    paddr = place.get("address") or place.get("vicinity") or "Address not available"
                    plat = place.get("lat") or place.get("latitude") or place.get("lng") or place.get("longitude")
                    plng = place.get("lng") or place.get("longitude") or place.get("lon") or place.get("long")

                    st.markdown(f"### ⭐ {pname}")
                    st.write(f"📍 Address: {paddr}")
                    if place.get("rating") is not None:
                        st.write(f"⭐ Rating: {place.get('rating')}")

                    # Show Bing Map iframe if lat/lng available, else skip
                    try:
                        if plat and plng:
                            bing_map_iframe = f"""
                            <iframe width="100%" height="300"
                                frameborder="0"
                                src="https://www.bing.com/maps/embed?h=300&w=800&cp={plat}~{plng}&lvl=14&typ=d&sty=r&src=SHELL&FORM=MBEDV8">
                            </iframe>
                            """
                            st.markdown("**🗺️ Map Preview:**", unsafe_allow_html=True)
                            st.markdown(bing_map_iframe, unsafe_allow_html=True)
                    except Exception:
                        pass

                    st.markdown("---")

                # Show aggregated Folium map with markers
                try:
                    m = folium.Map(location=[lat, lon], zoom_start=12, control_scale=True)
                    mc = MarkerCluster().add_to(m)
                    for place in places:
                        plat = place.get("lat") or place.get("latitude") or place.get("lng") or place.get("longitude")
                        plng = place.get("lng") or place.get("longitude") or place.get("lon") or place.get("long")
                        pname = place.get("name") or place.get("title") or "Place"
                        if plat and plng:
                            folium.Marker([plat, plng], popup=pname).add_to(mc)
                    st_folium(m, width="100%", height=450)
                except Exception:
                    # fallback: show Bing city map iframe
                    st.info("Could not render interactive map — showing city map instead.")
                    city_iframe = f"""
                    <iframe width="100%" height="400"
                        frameborder="0"
                        src="https://www.bing.com/maps/embed?h=400&w=800&cp={lat}~{lon}&lvl=11&typ=d&sty=r&src=SHELL&FORM=MBEDV8">
                    </iframe>
                    """
                    st.markdown(city_iframe, unsafe_allow_html=True)

        # ---------------- CRIME NEWS TAB ----------------
        with tabs[3]:
            st.header(f"Crime News in {city}")
            try:
                crime_list = get_crime_news(city) or []
            except Exception as e:
                crime_list = [{"title": "Error", "description": f"Crime fetch failed: {str(e)}"}]

            if not crime_list:
                st.info("No crime news found for this city.")
            else:
                for item in crime_list:
                    st.markdown(f"### 📰 {item.get('title','No title')}")
                    st.write(item.get("description",""))
                    st.write("---")

        # ---------------- EMERGENCY SERVICES TAB ----------------
        with tabs[4]:
            st.header("Emergency Services")
            try:
                services = get_osm_places("hospital", lat, lon) or []
            except Exception as e:
                services = [{"display_name": f"Error: {str(e)}"}]

            if not services:
                st.info("No emergency services found near this location.")
            else:
                for s in services:
                    name = s.get("display_name") or s.get("name") or "Unknown"
                    st.write(f"- {name}")

        # ---------------- TRENDS TAB ----------------
        with tabs[5]:
           import requests, pandas as pd, re, nltk, matplotlib.pyplot as plt
           from wordcloud import WordCloud
           from transformers import pipeline
           from bs4 import BeautifulSoup
           import streamlit as st
           import matplotlib
           from textblob import TextBlob

           def simple_sentiment(text):
             score = TextBlob(text).sentiment.polarity
             if score > 0: return "Positive"
             if score < 0: return "Negative"
             return "Neutral"

   

    
           st.header("🔥 City Trend Analysis (100% Free)")

           city_query = st.text_input("Enter city name:", value=city)

           if city_query:
            st.subheader("1️⃣ Wikipedia Popularity Trend")

            try:
                wiki_title = city_query.replace(" ", "_")
                url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/all-agents/{wiki_title}/daily/20240101/20241231"
                data = requests.get(url).json()

                df = pd.DataFrame(data["items"])
                df["views"] = df["views"]
                df["date"] = df["timestamp"].str[:8]

                st.line_chart(df.set_index("date")["views"])
            except:
                st.warning("Wikipedia trend data not available.")
            
            st.subheader("2️⃣ Reddit Travel Buzz (Free)")
            reddit_url = f"https://www.reddit.com/r/travel/search.json?q={city_query}&restrict_sr=1"
            headers = {"User-Agent": "Mozilla/5.0"}

            try:
                res = requests.get(reddit_url, headers=headers).json()
                posts = res["data"]["children"]

                titles = [p["data"]["title"] for p in posts][:15]
                joined = " ".join(titles)

                st.write("Top Reddit Topics:")
                for t in titles:
                     st.markdown(f"- {t}")
            except:
                st.info("No Reddit data found.")

            
            st.subheader("4️⃣ Trending Keywords")
            words = re.findall(r"[A-Za-z]+", joined.lower())
            freq = pd.Series(words).value_counts()[:15]

            st.bar_chart(freq)

            st.subheader("5️⃣ News Trend Highlights")

            news_url = f"https://news.google.com/rss/search?q={city_query}"

            try:
                xml = requests.get(news_url).text
                soup = BeautifulSoup(xml, "xml")
                items = soup.find_all("item")[:10]

                for it in items:
                    st.markdown(f"🔸 {it.title.text}")
            except:
                 st.info("News not available now.")

            st.subheader("6️⃣ Word Cloud Heatmap")
            try:
                 wc = WordCloud(width=800, height=400, background_color="black", colormap="viridis").generate(joined)
                 fig, ax = plt.subplots(figsize=(10, 5))
                 ax.imshow(wc, interpolation="bilinear")
                 ax.axis("off")
                 st.pyplot(fig)
            except:
                st.error("Could not generate word cloud.")
        

        # ---------------- CITYBOT TAB ----------------
        with tabs[6]:
            st.header("CityBot")
            if "history" not in st.session_state:
                st.session_state.history = []

            # Display existing chat history
            for m in st.session_state.history:
                try:
                    st.chat_message(m["role"]).write(m["text"])
                except Exception:
                    # fallback for older Streamlit versions
                    st.write(f"{m['role']}: {m['text']}")

            q = st.chat_input("Ask anything…")
            if q:
                st.session_state.history.append({"role": "user", "text": q})
                try:
                    ans = search_google(q) or "No answer returned."
                except Exception as e:
                    ans = f"Search failed: {str(e)}"
                st.session_state.history.append({"role": "assistant", "text": ans})
                try:
                    st.chat_message("assistant").write(ans)
                except Exception:
                    st.write(ans)
        

        # ---------------- MAPS TAB (Google Maps with AI place search) ----------------
        with tabs[7]:
             st.title("🗺️ Maps – Search Places & Directions")

             st.write("Type any location / tourist spot / landmark. Google Maps will load below.")

             place = st.text_input("Enter a place name (Example: Eiffel Tower, Taj Mahal, MG Road Bangalore)")
            
             if place:

                import urllib.parse
                q = urllib.parse.quote(place)
                 # Google Maps embed URL (no API key required)
                map_url = f"https://www.google.com/maps?q={q}&output=embed"

                st.components.v1.html(
            f"""
            <iframe 
                src="{map_url}"
                width="100%" 
                height="700" 
                style="border:0; border-radius:10px;" 
                allowfullscreen="" 
                loading="lazy">
            </iframe>
            """,
            height=720,
        )     
             else:
                st.info("🔍 Enter a place above to display it on Google Maps.")
        

        

        with tabs[8]:
            
            st.header("🧠 City Quiz")
            city_for_quiz = city



            city_for_quiz = st.selectbox("Select a city for quiz", city)

            if st.button("Generate Quiz"):
                with st.spinner("Creating quiz..."):
                    quiz = generate_city_quiz_gemini(city_for_quiz)

                if not quiz:
                    st.error("Could not generate quiz. Try again.")
                else:
                    st.success("Quiz Ready!")

            # Render questions
                    user_answers = {}

                    for i, q in enumerate(quiz):
                        st.write(f"### Q{i+1}. {q['question']}")
                        user_answers[i] = st.radio(
                        "Choose an option:",
                        q["options"],
                        key=f"quiz_q_{i}"
                        )
                        st.markdown("---")

            # Show Results
                    if st.button("Submit Answers"):
                        correct = 0
                        for i, q in enumerate(quiz):
                            if user_answers[i] == q["answer"]:
                                 correct += 1

                        st.subheader(f"🎉 You scored {correct}/{len(quiz)}!")
        

        with tabs[9]:
            st.subheader("🌍 Guess The City — Virtual Vacation")

            st.markdown("""
            <iframe 
            src="https://virtualvacation.us/maps" 
            width="100%" 
            height="700px" 
            style="border:none; border-radius:12px;">
            </iframe>
            """, unsafe_allow_html=True)

        # ----------------  REVIEWS TAB ----------------
        with tabs[10]:
            st.header(f"⭐ Reviews for {city}")
            
            # Initialize database
            init_reviews_db()
            
            # Get rating summary
            rating_summary, avg_rating, total_reviews = get_city_rating_summary(city)
            
            # Display rating summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Rating", f"{avg_rating:.1f}/5.0")
            with col2:
                st.metric("Total Reviews", total_reviews)
            with col3:
                st.markdown("**Rating Distribution**")
            
            # Show rating distribution
            rating_data = {
                "⭐⭐⭐⭐⭐": rating_summary[5],
                "⭐⭐⭐⭐": rating_summary[4],
                "⭐⭐⭐": rating_summary[3],
                "⭐⭐": rating_summary[2],
                "⭐": rating_summary[1]
            }
            
            st.bar_chart(pd.DataFrame([rating_data]).T.rename(columns={0: "Count"}))
            
            st.divider()
            
            # Add Review Section
            st.subheader("📝 Add Your Review")
            
            with st.form("review_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    review_title = st.text_input("Review Title", placeholder="What did you like?")
                
                with col2:
                    star_rating = st.selectbox(
                        "Rating",
                        options=[5, 4, 3, 2, 1],
                        format_func=lambda x: "⭐" * x
                    )
                
                review_text = st.text_area(
                    "Your Review",
                    placeholder="Share your experience about this city...",
                    height=120
                )
                
                # Image upload section
                st.subheader("📸 Add Photos")
                
                col_upload, col_camera = st.columns(2)
                
                uploaded_photo = None
                camera_photo = None
                
                with col_upload:
                    st.write("**Upload from Local Storage**")
                    uploaded_photo = st.file_uploader(
                        "Choose an image",
                        type=["jpg", "jpeg", "png", "gif", "bmp"],
                        key="photo_upload"
                    )
                
                with col_camera:
                    st.write("**Take Photo with Camera**")
                    camera_photo = st.camera_input("Capture a photo")
                
                # Choose which photo to use
                final_photo = None
                photo_filename = None
                
                if camera_photo is not None:
                    final_photo = camera_photo.read()
                    photo_filename = f"camera_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    st.success("✅ Camera photo captured!")
                elif uploaded_photo is not None:
                    final_photo = uploaded_photo.read()
                    photo_filename = uploaded_photo.name
                    st.success("✅ Photo uploaded!")
                
                # Preview photo if available
                if final_photo is not None:
                    st.image(final_photo, caption="Photo Preview", use_column_width=True, width=300)
                
                # Submit button
                submit_button = st.form_submit_button("✅ Submit Review", use_container_width=True)
                
                if submit_button:
                    if not review_title.strip():
                        st.error("❌ Please enter a review title")
                    elif not review_text.strip():
                        st.error("❌ Please write a review")
                    else:
                        # Process photo if exists
                        photo_bytes = None
                        if final_photo is not None:
                            try:
                                img = Image.open(io.BytesIO(final_photo))
                                # Resize if too large
                                max_size = (800, 800)
                                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                                
                                img_byte_arr = io.BytesIO()
                                img.save(img_byte_arr, format='JPEG', quality=85)
                                img_byte_arr.seek(0)
                                photo_bytes = img_byte_arr.getvalue()
                            except Exception as e:
                                st.warning(f"⚠️ Could not process image: {str(e)}")
                        
                        # Add review to database
                        try:
                            add_review(city, star_rating, review_title, review_text, photo_bytes, photo_filename)
                            st.success("✅ Review submitted successfully!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ Error saving review: {str(e)}")
            
            st.divider()
            
            # Display Reviews
            st.subheader("📖 All Reviews")
            
            reviews = get_reviews_for_city(city)
            
            if not reviews:
                st.info(f"😴 No reviews yet for {city}. Be the first to review!")
            else:
                # Filter by rating
                filter_rating = st.selectbox(
                    "Filter by Rating",
                    options=[0, 5, 4, 3, 2, 1],
                    format_func=lambda x: "All Ratings" if x == 0 else "⭐" * x,
                    key="filter_rating"
                )
                
                filtered_reviews = reviews if filter_rating == 0 else [r for r in reviews if r['rating'] == filter_rating]
                
                if not filtered_reviews:
                    st.info(f"No reviews with {filter_rating} stars")
                else:
                    for i, review in enumerate(filtered_reviews):
                        with st.container(border=True):
                            col_rating, col_title, col_date = st.columns([1, 2, 1])
                            
                            with col_rating:
                                st.markdown(f"### {'⭐' * review['rating']}")
                            
                            with col_title:
                                st.subheader(review['title'])
                            
                            with col_date:
                                st.caption(review['created_at'][:10] if review['created_at'] else "")
                            
                            st.write(review['text'])
                            
                            # Display photo if exists
                            if review['photo_data'] is not None:
                                try:
                                    img = load_image_from_bytes(review['photo_data'])
                                    if img:
                                        st.image(img, caption=review['photo_filename'] or "Review Photo", use_column_width=True, width=400)
                                except Exception as e:
                                    st.warning(f"Could not display image: {str(e)}")
                            
                            # Delete button
                            if st.button(f"🗑️ Delete Review {review['id']}", key=f"delete_{review['id']}"):
                                try:
                                    delete_review(review['id'])
                                    st.success("✅ Review deleted!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting review: {str(e)}")


        
            
    


       

        

        


        

        
        

          
    
  
           

    
   
            

    

