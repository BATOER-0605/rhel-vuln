from __future__ import annotations

from datetime import date
from typing import Any

from .filter import matches_rhel
from .redhat_client import RedHatClient
from .schemas import (
    FilterMode,
    QueryEcho,
    QueryParams,
    RhsaSummary,
    SearchResponse,
)


def month_bounds(month: str) -> tuple[date, date]:
    """Return [after, before) covering the given YYYY-MM month."""
    year_s, month_s = month.split("-")
    year, m = int(year_s), int(month_s)
    after = date(year, m, 1)
    before = date(year + 1, 1, 1) if m == 12 else date(year, m + 1, 1)
    return after, before


def _normalize_cves(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _normalize_bugs(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _rhsa_url(rhsa_id: str) -> str:
    return f"https://access.redhat.com/errata/{rhsa_id}"


def to_summary(entry: dict[str, Any]) -> RhsaSummary:
    rhsa_id = entry.get("RHSA") or entry.get("id") or ""
    return RhsaSummary(
        rhsa_id=rhsa_id,
        title=entry.get("synopsis") or entry.get("title"),
        severity=entry.get("severity"),
        released_on=entry.get("released_on"),
        cves=_normalize_cves(entry.get("CVEs")),
        bugzilla_ids=_normalize_bugs(entry.get("bugzilla")),
        affected_packages=list(entry.get("released_packages") or []),
        resource_url=entry.get("resource_url"),
        rhsa_url=_rhsa_url(rhsa_id) if rhsa_id else None,
    )


async def find_rhsa_for_month(
    params: QueryParams,
    client: RedHatClient | None = None,
) -> SearchResponse:
    after, before = month_bounds(params.month)
    mode: FilterMode = params.effective_mode()

    owns = client is None
    client = client or RedHatClient()
    try:
        entries = await client.list_advisories(after, before)
    finally:
        if owns:
            await client.aclose()

    matched = [e for e in entries if matches_rhel(e, params.major, params.minor, mode)]
    results = [to_summary(e) for e in matched]
    results.sort(key=lambda r: (r.released_on or "", r.rhsa_id))

    return SearchResponse(
        query=QueryEcho(
            major=params.major,
            minor=params.minor,
            month=params.month,
            mode=mode,
        ),
        count=len(results),
        results=results,
    )
