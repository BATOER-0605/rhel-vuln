from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from .schemas import FilterMode


@lru_cache(maxsize=128)
def _minor_pattern(major: int, minor: int) -> re.Pattern[str]:
    # Match e.g. ".el8_4." or ".el8_4-" or ".el8_4" at end of token.
    return re.compile(rf"\.el{major}_{minor}(?:[.\-_]|$)")


@lru_cache(maxsize=64)
def _major_pattern(major: int) -> re.Pattern[str]:
    # Match ".el8" or ".el8_X" or ".el8." etc. Anything starting with .elX.
    return re.compile(rf"\.el{major}(?:[._\-]|$)")


def matches_rhel(
    entry: dict[str, Any],
    major: int,
    minor: int | None,
    mode: FilterMode,
) -> bool:
    """Return True if the RHSA list entry targets the requested RHEL version.

    Decision is based on Red Hat's package NVR tags (`.elX` / `.elX_Y`)
    found inside the entry's ``released_packages`` list.

    - mode=major: any package tagged ``.elX``.
    - mode=minor: a package tagged ``.elX_Y`` (minor-specific stream, e.g. EUS)
      OR a generic ``.elX`` package (applies to all minors of major X).
      The latter is included because security errata for the GA stream do
      apply to systems running X.Y.
    """
    packages = entry.get("released_packages") or []
    if not packages:
        return False

    major_re = _major_pattern(major)

    if mode is FilterMode.major or minor is None:
        return any(major_re.search(pkg) for pkg in packages)

    minor_re = _minor_pattern(major, minor)
    has_minor = any(minor_re.search(pkg) for pkg in packages)
    if has_minor:
        return True

    # Fall back to generic .elX packages, but only if NONE of the packages
    # carry a *different* minor stream (which would indicate this errata is
    # for another EUS/AUS minor, not for the requested one).
    other_minor_re = re.compile(rf"\.el{major}_(\d+)")
    other_minors = {m.group(1) for pkg in packages for m in [other_minor_re.search(pkg)] if m}
    if other_minors and str(minor) not in other_minors:
        return False
    return any(major_re.search(pkg) for pkg in packages)
