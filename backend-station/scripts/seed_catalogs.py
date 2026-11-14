"""Seed the fixed branches and initial fuel catalog."""

from sqlalchemy import select

from app.database import SessionLocal
from app.tables import Branch, FuelType

BRANCHES = (("SAN_JOSE", "San José"), ("SANTA_MARTA", "Santa Marta"))
FUEL_TYPES = (("DIESEL_S50", "Diesel S50"), ("GASOLINA_90", "Gasolina 90"))


if __name__ == "__main__":
    with SessionLocal.begin() as db:
        for code, name in BRANCHES:
            if db.scalar(select(Branch).where(Branch.code == code)) is None:
                db.add(Branch(code=code, name=name))
        for code, name in FUEL_TYPES:
            if db.scalar(select(FuelType).where(FuelType.code == code)) is None:
                db.add(FuelType(code=code, name=name))
    print("Catalog seeds applied")
