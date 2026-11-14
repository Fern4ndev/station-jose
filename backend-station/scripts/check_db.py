"""Check PostgreSQL connectivity."""

from sqlalchemy import text

from app.database import engine


if __name__ == "__main__":
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database connection OK")
