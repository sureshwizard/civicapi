import os

DB_PATH = (
    os.environ.get("DB_PATH")
    or os.environ.get("CIVICAPI_DB_PATH")
    or "civicapi.sqlite3"  # fallback
)
