"""
db.py
This file is responsible for establishing the connection to the PostgreSQL database.
Database credentials are loaded from the .env file.
"""

import psycopg2
import os
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

def get_connection():
    """
    Creates and returns a database connection.
    Returns None if the connection fails.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )
        cur = conn.cursor()
        cur.execute("SET search_path TO universe")
        cur.close()
        return conn 
    except Exception as error:
        print(error)
        return None
