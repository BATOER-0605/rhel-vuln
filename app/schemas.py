from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class FilterMode(str, Enum):
    minor = "minor"
    major = "major"


class QueryParams(BaseModel):
    major: int = Field(..., ge=5, le=99, description="RHEL major version (e.g. 8)")
    minor: Optional[int] = Field(
        None, ge=0, le=99, description="RHEL minor version (e.g. 4). Optional."
    )
    month: str = Field(..., description="Target month in YYYY-MM format")
    mode: Optional[FilterMode] = Field(
        None,
        description=(
            "Filter mode. 'minor' includes both .elX_Y and .elX packages. "
            "'major' includes any package tagged for major X. "
            "Defaults to 'minor' when minor is given, else 'major'."
        ),
    )

    @field_validator("month")
    @classmethod
    def _validate_month(cls, v: str) -> str:
        if not MONTH_RE.match(v):
            raise ValueError("month must be YYYY-MM (e.g. 2024-09)")
        return v

    def effective_mode(self) -> FilterMode:
        if self.mode is not None:
            return self.mode
        return FilterMode.minor if self.minor is not None else FilterMode.major


class RhsaSummary(BaseModel):
    rhsa_id: str
    title: Optional[str] = None
    severity: Optional[str] = None
    released_on: Optional[str] = None
    cves: list[str] = Field(default_factory=list)
    bugzilla_ids: list[str] = Field(default_factory=list)
    affected_packages: list[str] = Field(default_factory=list)
    resource_url: Optional[str] = None
    rhsa_url: Optional[str] = None


class QueryEcho(BaseModel):
    major: int
    minor: Optional[int]
    month: str
    mode: FilterMode


class SearchResponse(BaseModel):
    query: QueryEcho
    count: int
    results: list[RhsaSummary]
