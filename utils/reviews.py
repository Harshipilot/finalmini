# reviews.py
import sqlite3
import json
import base64
import os
from datetime import datetime
from pathlib import Path
import io
from PIL import Image

# Database path
DB_PATH = "reviews.db"

def init_reviews_db():
    """Initialize the reviews database if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create reviews table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            rating INTEGER NOT NULL,
            title TEXT NOT NULL,
            review_text TEXT NOT NULL,
            photo_data BLOB,
            photo_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def add_review(city, rating, title, review_text, photo_bytes=None, photo_filename=None):
    """Add a review to the database."""
    init_reviews_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO reviews (city, rating, title, review_text, photo_data, photo_filename)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (city, rating, title, review_text, photo_bytes, photo_filename))
    
    conn.commit()
    conn.close()
    return True

def get_reviews_for_city(city):
    """Get all reviews for a specific city."""
    init_reviews_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, rating, title, review_text, photo_data, photo_filename, created_at
        FROM reviews
        WHERE city = ?
        ORDER BY created_at DESC
    """, (city,))
    
    reviews = cursor.fetchall()
    conn.close()
    
    result = []
    for review in reviews:
        result.append({
            'id': review[0],
            'rating': review[1],
            'title': review[2],
            'text': review[3],
            'photo_data': review[4],
            'photo_filename': review[5],
            'created_at': review[6]
        })
    
    return result

def get_city_rating_summary(city):
    """Get rating summary for a city."""
    init_reviews_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT rating, COUNT(*) as count
        FROM reviews
        WHERE city = ?
        GROUP BY rating
        ORDER BY rating DESC
    """, (city,))
    
    ratings = cursor.fetchall()
    conn.close()
    
    summary = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for rating, count in ratings:
        summary[rating] = count
    
    total = sum(summary.values())
    if total > 0:
        average = sum(r * summary[r] for r in range(1, 6)) / total
    else:
        average = 0
    
    return summary, average, total

def delete_review(review_id):
    """Delete a review from the database."""
    init_reviews_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    
    conn.commit()
    conn.close()
    return True

def process_image(image_data):
    """Convert image to bytes for storage."""
    if image_data is None:
        return None
    
    # If it's already bytes, return as is
    if isinstance(image_data, bytes):
        return image_data
    
    # If it's a PIL Image, convert to bytes
    if hasattr(image_data, 'save'):
        img_byte_arr = io.BytesIO()
        image_data.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()
    
    return None

def load_image_from_bytes(image_bytes):
    """Load PIL Image from bytes."""
    if image_bytes is None:
        return None
    
    return Image.open(io.BytesIO(image_bytes))
