import psycopg2
import os
from dotenv import load_dotenv

# Loads enviroment variables from .env file
load_dotenv()

"""
Creates and returns a connection to the PostgresSQL. 
Database är loaded from the .env file. 
Returns None if the connection fails. 
"""
def get_connection():
    try:
        conn = psycopg2.connect(
            host = os.getenv("DB_HOST"),
            dbname = os.getenv("DB_NAME"),
            user = os.getenv("DB_USER"),
            password = os.getenv("DB_PASSWORD"),
            port = os.getenv("DB_PORT")
        )
        cur = conn.cursor()
        cur.execute("SET search_path TO universe")
        cur.close()
        return conn 
    except Exception as error:
        print(error)
        return None
