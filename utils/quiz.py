import google.generativeai as genai
import json
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

def generate_city_quiz_gemini(city_name: str):
    """
    Generates a 5-question MCQ quiz for the selected city using Gemini API.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
    Create a fun and interactive 5-question multiple-choice quiz about the city "{city_name}".
    Return ONLY clean JSON in this format:
    {{
      "quiz": [
        {{
          "question": "...",
          "options": ["A", "B", "C", "D"],
          "answer": "B"
        }}
      ]
    }}
    }}
    """

    response = model.generate_content(prompt)

    # Extract text
    text = response.text.strip()

    # Ensure valid JSON
    text = text.replace("```json", "").replace("```", "")

    try:
        data = json.loads(text)
        return data.get("quiz", [])
    except:
        return []
