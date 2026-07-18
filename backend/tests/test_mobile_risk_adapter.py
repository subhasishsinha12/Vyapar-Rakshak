"""Unit tests for the mobile-risk adapter (Mock provider). No live server needed."""
import pytest

from adapters.mobile_risk import MockMobileRiskAdapter


@pytest.mark.asyncio
async def test_invalid_number_rejected_without_retry():
    a = MockMobileRiskAdapter()
    env = await a.check("12345")
    assert env["ok"] is False
    assert env["error"] == "Mobile number invalid"


@pytest.mark.asyncio
async def test_seeded_number_is_very_high_risk_and_recommends_block():
    a = MockMobileRiskAdapter()
    env = await a.check("9099911234")
    assert env["ok"] is True
    assert env["risk_level"] == "very_high"
    assert env["recommendation"] == "block"
    assert env["mobile_number_masked"] == "XXXXXX1234"


@pytest.mark.asyncio
async def test_result_is_cached_on_repeat_check():
    a = MockMobileRiskAdapter()
    env1 = await a.check("9876543210")
    env2 = await a.check("9876543210")
    assert env1["cached"] is False
    assert env2["cached"] is True
    assert env1["risk_level"] == env2["risk_level"]


@pytest.mark.asyncio
async def test_country_code_prefix_normalised_same_as_bare_number():
    a = MockMobileRiskAdapter()
    bare = await a.check("7771234567")
    prefixed = await a.check("+91 77712 34567")
    assert bare["risk_level"] == prefixed["risk_level"] == "high"
