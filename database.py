import pyodbc
import pandas as pd
import os
from dotenv import load_dotenv
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

load_dotenv()

DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_TRUSTED_CONNECTION = os.getenv("DB_TRUSTED_CONNECTION", "true").lower() == "true"
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def get_connection():
    """SQL Server ilə əlaqə yaradır (həm local, həm də server üçün)"""
    if DB_TRUSTED_CONNECTION:
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_NAME};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;")
    else:
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_NAME};"
            f"UID={DB_USERNAME};"
            f"PWD={DB_PASSWORD};"
            "TrustServerCertificate=yes;")

    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"❌ Database qoşulma xətası: {e}")
        return None


def execute_query(query, params=None):
    """SQL sorğusu icra edir və DataFrame qaytarır"""
    conn = get_connection()
    if conn is None:
        return None
    
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    except Exception as e:
        print(f"❌ Sorğu icra xətası: {e}")
        return None
    finally:
        conn.close()


def insert_data(query, params=None):
    """Verilənləri bazaya əlavə edir"""
    conn = get_connection()
    if conn is None:
        return False
    
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Data əlavə xətası: {e}")
        conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        conn.close()


def execute_non_query(query, params=None):
    """INSERT, UPDATE, DELETE sorğuları üçün (affected rows qaytarır)"""
    conn = get_connection()
    if conn is None:
        return 0
    
    cursor = None
    try:
        cursor = conn.cursor()
        
        if isinstance(params, list) and len(params) > 0 and isinstance(params[0], tuple):
            cursor.executemany(query, params)
        else:
            cursor.execute(query, params or ())
        
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        print(f"❌ Sorğu icra xətası: {e}")
        conn.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        conn.close()