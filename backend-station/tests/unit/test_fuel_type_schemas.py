"""Fuel type request schema validation tests."""

import pytest
from app.schemas.catalog import FuelTypeCreate, FuelTypeUpdate
from pydantic import ValidationError


def test_name_is_normalized() -> None:
    fuel = FuelTypeCreate(name="  Diésel   S50 ")

    assert fuel.name == "Diésel S50"


def test_blank_name_is_rejected() -> None:
    with pytest.raises(ValidationError, match="obligatorio"):
        FuelTypeCreate(name="   ")


def test_update_only_accepts_name() -> None:
    update = FuelTypeUpdate(name="  Gasohol   Regular ")

    assert update.name == "Gasohol Regular"
