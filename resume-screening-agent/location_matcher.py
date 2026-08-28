"""Location clustering: a search for one city in a metro/region also matches
resumes from other cities in the same cluster (e.g. Delhi NCR, Mumbai/Pune)."""

from __future__ import annotations

import re

LOCATION_CLUSTERS: dict[str, set[str]] = {
    "delhi_ncr": {
        "delhi", "new delhi", "ncr", "delhi ncr",
        "noida", "gurgaon", "gurugram", "ghaziabad", "faridabad",
    },
    "mumbai_pune": {"mumbai", "pune", "navi mumbai", "thane"},
}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()


def resolve_cluster(location_text: str | None) -> str | None:
    """Return the canonical cluster name a free-text location belongs to, or None
    if it's blank or doesn't match any known cluster (e.g. "Remote", "Austin, TX")."""
    if not location_text:
        return None
    normalized = f" {_normalize(location_text)} "
    for cluster, aliases in LOCATION_CLUSTERS.items():
        if any(f" {alias} " in normalized for alias in aliases):
            return cluster
    return None
