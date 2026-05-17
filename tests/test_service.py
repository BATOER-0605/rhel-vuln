import json
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

from app.redhat_client import RedHatClient
from app.schemas import FilterMode, QueryParams
from app.service import find_rhsa_for_month, month_bounds

FIXTURE = Path(__file__).parent / "fixtures" / "csaf_sample.json"


def load_fixture():
    return json.loads(FIXTURE.read_text())


class TestMonthBounds:
    def test_regular_month(self):
        a, b = month_bounds("2024-09")
        assert a == date(2024, 9, 1)
        assert b == date(2024, 10, 1)

    def test_december_wraps_year(self):
        a, b = month_bounds("2024-12")
        assert a == date(2024, 12, 1)
        assert b == date(2025, 1, 1)

    def test_january(self):
        a, b = month_bounds("2024-01")
        assert a == date(2024, 1, 1)
        assert b == date(2024, 2, 1)


@pytest.mark.asyncio
async def test_find_rhsa_minor_mode():
    fixture = load_fixture()
    async with httpx.AsyncClient() as http:
        with respx.mock(assert_all_called=True) as router:
            router.get("https://access.redhat.com/hydra/rest/securitydata/csaf.json").mock(
                return_value=httpx.Response(200, json=fixture)
            )
            client = RedHatClient(client=http)
            params = QueryParams(major=8, minor=4, month="2024-09", mode=FilterMode.minor)
            resp = await find_rhsa_for_month(params, client=client)
    rhsa_ids = {r.rhsa_id for r in resp.results}
    assert "RHSA-2024:6500" in rhsa_ids
    assert "RHSA-2024:6800" in rhsa_ids
    assert "RHSA-2024:6600" not in rhsa_ids
    assert "RHSA-2024:6700" not in rhsa_ids
    assert resp.count == len(resp.results)


@pytest.mark.asyncio
async def test_find_rhsa_major_mode_rhel9():
    fixture = load_fixture()
    async with httpx.AsyncClient() as http:
        with respx.mock(assert_all_called=True) as router:
            router.get("https://access.redhat.com/hydra/rest/securitydata/csaf.json").mock(
                return_value=httpx.Response(200, json=fixture)
            )
            client = RedHatClient(client=http)
            params = QueryParams(major=9, month="2024-09", mode=FilterMode.major)
            resp = await find_rhsa_for_month(params, client=client)
    rhsa_ids = [r.rhsa_id for r in resp.results]
    assert rhsa_ids == ["RHSA-2024:6600"]


@pytest.mark.asyncio
async def test_find_rhsa_major_mode_rhel8_all():
    fixture = load_fixture()
    async with httpx.AsyncClient() as http:
        with respx.mock(assert_all_called=True) as router:
            router.get("https://access.redhat.com/hydra/rest/securitydata/csaf.json").mock(
                return_value=httpx.Response(200, json=fixture)
            )
            client = RedHatClient(client=http)
            params = QueryParams(major=8, month="2024-09", mode=FilterMode.major)
            resp = await find_rhsa_for_month(params, client=client)
    rhsa_ids = {r.rhsa_id for r in resp.results}
    assert rhsa_ids == {
        "RHSA-2024:6464",
        "RHSA-2024:6500",
        "RHSA-2024:6700",
        "RHSA-2024:6800",
    }


@pytest.mark.asyncio
async def test_find_rhsa_propagates_api_error():
    from app.redhat_client import RedHatAPIError

    async with httpx.AsyncClient() as http:
        with respx.mock() as router:
            router.get(
                "https://access.redhat.com/hydra/rest/securitydata/csaf.json"
            ).mock(return_value=httpx.Response(503))
            client = RedHatClient(client=http)
            params = QueryParams(major=8, month="2024-09")
            with pytest.raises(RedHatAPIError):
                await find_rhsa_for_month(params, client=client)


def test_query_params_rejects_bad_month():
    with pytest.raises(ValueError):
        QueryParams(major=8, month="2024-13")


def test_query_params_effective_mode_defaults():
    assert QueryParams(major=8, minor=4, month="2024-09").effective_mode() == FilterMode.minor
    assert QueryParams(major=8, month="2024-09").effective_mode() == FilterMode.major
