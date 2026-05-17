from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class RedHatAPIError(RuntimeError):
    """Raised when the Red Hat Security Data API cannot be reached or returns an error."""


class RedHatClient:
    BASE_URL = "https://access.redhat.com/hydra/rest/securitydata"
    USER_AGENT = "rhel-vuln-scanner/0.1 (+https://github.com/batoer-0605/rhel-vuln)"
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    PER_PAGE = 1000

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"},
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "RedHatClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def list_advisories(self, after: date, before: date) -> list[dict[str, Any]]:
        """List CSAF (RHSA) entries released in [after, before).

        Uses the `/csaf.json` endpoint. The CVRF endpoint was deprecated and
        removed by Red Hat; CSAF returns the same list-shape fields
        (``RHSA``, ``severity``, ``released_on``, ``released_packages``, ...).
        """
        url = f"{self.BASE_URL}/csaf.json"
        all_rows: list[dict[str, Any]] = []
        page = 1
        while True:
            params = {
                "after": after.isoformat(),
                "before": before.isoformat(),
                "per_page": self.PER_PAGE,
                "page": page,
            }
            rows = await self._get_json(url, params)
            if not isinstance(rows, list):
                raise RedHatAPIError(
                    f"Unexpected response shape from {url}: {type(rows).__name__}"
                )
            all_rows.extend(rows)
            if len(rows) < self.PER_PAGE:
                break
            page += 1
        return all_rows

    async def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        last_exc: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_exc = exc
                logger.warning(
                    "Red Hat API request failed (attempt %d/%d): %s",
                    attempt,
                    self.MAX_RETRIES,
                    exc,
                )
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(2 ** (attempt - 1))
        raise RedHatAPIError(
            f"Failed to reach Red Hat Security Data API after {self.MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc
