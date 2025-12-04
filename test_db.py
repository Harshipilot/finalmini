#!/usr/bin/env python
"""Quick test to verify reviews database setup"""
import sqlite3
import os

db_file = 'reviews.db'
if os.path.exists(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    conn.close()
    print("✅ Database file exists")
    print(f"📊 Tables: {[t[0] for t in tables]}")
else:
    print("Database will be created on first use")
