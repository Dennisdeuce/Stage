"""Generic HTML scraper (§3.1 last resort).

Fragile by nature — wrapped in source-health monitoring by the pipeline. Use only
when a venue has no .ics/RSS/JSON feed. Everything is config-driven via CSS
selectors so most venues need no bespoke code.

config:
  page_url:   the calendar page to scrape
  venue_slug: registry slug (single-venue pages)
  base_url:   for resolving relative hrefs (default = page_url origin)
  selectors:  { item, title, date, url, image, description, price, venue }
  date_attr:  optional attribute to read the date from (e.g. "datetime")
  tz:         optional timezone

Multi-venue listing pages (e.g. a promoter site covering several rooms) may
route items like the STG adapter does:
  venue_map:          { "venue display name substring": "registry-slug", ... }
  default_venue_slug: fallback when the venue text matches nothing; when
                      omitted, unmatched items are dropped (out-of-network).
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from models import RawEvent
from .base import HttpClient

_DASH = re.compile(r"\s+[-–—]\s+|\s*[–—]\s*")
_YEAR = re.compile(r"\b20\d\d\b")


def parse_event_date(text: str):
    """Parse a human event date, tolerating ranges like "Jul 20 - 24, 2026"
    or "July 07 - August 05" by keeping the range start (plus the year, which
    sites usually print only at the end)."""
    candidates = [text]
    parts = _DASH.split(text, maxsplit=1)
    if len(parts) == 2 and parts[0].strip():
        start = parts[0].strip()
        year = _YEAR.search(text)
        if year and not _YEAR.search(start):
            start = f"{start} {year.group()}"
        candidates.insert(0, start)
    for cand in candidates:
        try:
            return dateparser.parse(cand, fuzzy=True)
        except (ValueError, OverflowError):
            continue
    return None


class HTMLAdapter:
    kind = "html"

    def __init__(self, slug: str, config: dict[str, Any], http: HttpClient):
        self.slug = slug
        self.config = config
        self.http = http

    def _text(self, node, selector):
        if not selector or node is None:
            return None
        el = node.select_one(selector)
        # Space-join so sibling spans ("Jul" "7" "2026") stay parseable.
        return " ".join(el.get_text(" ", strip=True).split()) if el else None

    def fetch(self) -> list[RawEvent]:
        cfg = self.config
        page_url = cfg["page_url"]
        venue_slug = cfg.get("venue_slug")
        venue_map: dict[str, str] = cfg.get("venue_map") or {}
        base_url = cfg.get("base_url", page_url)
        tz = cfg.get("tz", "America/Los_Angeles")
        sel = cfg["selectors"]
        date_attr = cfg.get("date_attr")

        resp = self.http.get(page_url)
        soup = BeautifulSoup(resp.text, "lxml")

        events: list[RawEvent] = []
        for node in soup.select(sel["item"]):
            title = self._text(node, sel.get("title"))
            if not title:
                continue

            # Venue routing for multi-venue pages (mirrors the STG adapter).
            item_venue = venue_slug
            if venue_map:
                vtext = (self._text(node, sel.get("venue")) or "").lower()
                item_venue = next(
                    (slug for name, slug in venue_map.items() if name.lower() in vtext),
                    cfg.get("default_venue_slug"),
                )
                if not item_venue:
                    continue  # out-of-network venue — drop

            # Date: from an attribute (e.g. <time datetime="...">) or text.
            date_val = None
            if date_attr and sel.get("date"):
                el = node.select_one(sel["date"])
                if el and el.has_attr(date_attr):
                    date_val = el[date_attr]
            if not date_val:
                date_val = self._text(node, sel.get("date"))
            starts_at = parse_event_date(date_val) if date_val else None

            # Link
            url = None
            if sel.get("url"):
                a = node.select_one(sel["url"])
                if a and a.has_attr("href"):
                    url = urljoin(base_url, a["href"])

            # Image
            image_url = None
            if sel.get("image"):
                img = node.select_one(sel["image"])
                if img and img.has_attr("src"):
                    image_url = urljoin(base_url, img["src"])

            events.append(
                RawEvent(
                    source_slug=self.slug,
                    venue_slug=item_venue,
                    title=title,
                    starts_at=starts_at,
                    tz=tz,
                    description=self._text(node, sel.get("description")),
                    image_url=image_url,
                    source_url=url,
                    venue_primary_url=url,
                    raw={},
                )
            )
        return events
