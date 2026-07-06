"""Validate the seeded source configs against the live sites.

Runs every verified (non-TM) source in seed_venues through its real adapter
and reports how many events parsed and whether titles/dates/links look sane.
Use this when tuning selectors or re-checking after a venue redesign:

    python verify_sources.py            # verified sources only
    python verify_sources.py --all      # also try the generic-selector ones

Network-dependent by design — it is a maintenance tool, not a CI test.
"""
from __future__ import annotations

import sys

from adapters import build_adapter
from adapters.base import HttpClient
from seed_venues import source_rows


def check(source: dict) -> tuple[str, str]:
    slug = source["slug"]
    try:
        adapter = build_adapter(source, HttpClient())
        events = adapter.fetch()
    except Exception as e:  # noqa: BLE001 — report, don't crash the sweep
        return "ERR", f"{type(e).__name__}: {str(e)[:90]}"
    if not events:
        return "EMPTY", "0 events"
    dated = sum(1 for e in events if e.starts_at is not None)
    linked = sum(1 for e in events if e.source_url or e.venue_primary_url)
    sample = events[0]
    when = sample.starts_at.date() if sample.starts_at else "??"
    status = "OK" if dated >= len(events) * 0.8 and linked >= len(events) * 0.8 else "WEAK"
    return status, (
        f"{len(events)} events, {dated} dated, {linked} linked · "
        f"e.g. {sample.title[:40]!r} @ {sample.venue_slug} on {when}"
    )


def main() -> int:
    include_all = "--all" in sys.argv
    failures = 0
    for source in source_rows():
        if source["kind"] in ("ticketmaster",):  # needs an API key
            continue
        if not include_all and not source["config"].get("verified"):
            continue
        status, detail = check(source)
        print(f"{status:5s} {source['slug']:26s} {detail}")
        if status in ("ERR", "EMPTY"):
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
