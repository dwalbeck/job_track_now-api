#!/usr/bin/env python3
"""
Wait for PostgreSQL database to be ready before starting the application.
"""
import os
import time
import psycopg2
from psycopg2 import OperationalError


def wait_for_db():
    """Wait for database to be available."""
    # Get individual database components from environment
    db_host = os.getenv('DATABASE_HOST')
    db_user = os.getenv('DATABASE_USER')
    db_pass = os.getenv('DATABASE_PASS')
    db_name = os.getenv('DATABASE_DB')
    db_port = os.getenv('DATABASE_PORT')

    # Build database URL from components
    db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    # Parse database URL
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Try to connect to database
            conn = psycopg2.connect(db_url)
            conn.close()
            print("✅ Database is ready!")
            return True
        except OperationalError as e:
            retry_count += 1
            print(f"⏳ Waiting for database... (attempt {retry_count}/{max_retries})")
            if retry_count >= max_retries:
                print(f"❌ Failed to connect to database after {max_retries} attempts")
                print(f"Error: {e}")
                return False
            time.sleep(2)

    return False


if __name__ == "__main__":
    if wait_for_db():
        print("🚀 Starting application...")
        os.system("uvicorn app.main:app --host 0.0.0.0 --port 7080")
    else:
        exit(1)