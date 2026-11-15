"""Check PostgreSQL connectivity."""

from app.database import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database connection OK")
