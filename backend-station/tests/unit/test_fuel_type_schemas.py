"""Fuel type request schema validation tests."""

import pytest
from app.schemas.catalog import FuelTypeCreate, FuelTypeUpdate
from pydantic import ValidationError


def test_code_is_normalized_to_upper_snake_case() -> None:
    fuel = FuelTypeCreate(code="  diesel s50  ", name="  Diésel   S50 ")

    assert fuel.code == "DIESEL-S50"
    assert fuel.name == "Diésel S50"
    assert fuel.is_active is True


def test_blank_name_is_rejected() -> None:
    with pytest.raises(ValidationError, match="obligatorio"):
        FuelTypeCreate(code="DIESEL-S50", name="   ")


def test_invalid_code_characters_are_rejected() -> None:
    with pytest.raises(ValidationError, match="solo admite"):
        FuelTypeCreate(code="DIESEL@S50", name="Diésel S50")


def test_update_only_accepts_name() -> None:
    update = FuelTypeUpdate(name="  Gasohol   Regular ")

    assert update.name == "Gasohol Regular"
