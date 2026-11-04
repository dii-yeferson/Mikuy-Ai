from datetime import date

import pytest
from app.catalog import BY_ID, compatible
from app.domain import create_catalog_plan
from app.schemas import ProfileIn
from fastapi import HTTPException
from pydantic import ValidationError


def test_structured_unknown_or_wrong_kind_recipe_rejected():
    with pytest.raises(HTTPException) as error:
        create_catalog_plan(ProfileIn(), date(2026, 10, 19), ["sopa-lentejas"] * 21)
    assert error.value.status_code == 502
    with pytest.raises(HTTPException):
        create_catalog_plan(ProfileIn(), date(2026, 10, 19), ["inventada"] * 21)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1])
def test_non_finite_profile(bad):
    with pytest.raises(ValidationError):
        ProfileIn(budget=bad)


def test_normalized_exclusion_and_pescetarian():
    assert not compatible(BY_ID["pollo-horno"], ProfileIn(diet="Pescetariano"))
    assert compatible(BY_ID["sudado-pescado"], ProfileIn(diet="Pescetariano"))
    assert not compatible(BY_ID["pan-palta-huevo"], ProfileIn(excluded=["AGUACATE"]))


def test_conditions_filter_red_recipes_and_add_adjustments():
    from app.catalog import traffic

    p = ProfileIn(health=["diabetes", "hipertension"], budget=200)
    plan = create_catalog_plan(p, date(2026, 10, 19))
    assert len(plan["meals"]) == 21
    for m in plan["meals"]:
        lights = traffic(BY_ID[m["recipe_id"]])
        assert lights["diabetes"] != "rojo" and lights["hipertension"] != "rojo"
        assert m["adjustments"], m["recipe_id"]
    assert plan["conditions"] == ["diabetes", "hipertension"]


def test_budget_first_replaces_expensive_meals():
    rich = create_catalog_plan(ProfileIn(servings=4, budget=3000), date(2026, 10, 19))
    cheap = create_catalog_plan(ProfileIn(servings=4, budget=rich["cost"] - 25), date(2026, 10, 19))
    assert cheap["cost"] <= rich["cost"] - 25
