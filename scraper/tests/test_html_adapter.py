"""Offline tests for the HTML adapter's parsing behaviors added while
live-verifying venue selectors (venue routing, date ranges, span joining)."""
from __future__ import annotations

from adapters.html import HTMLAdapter, parse_event_date


class FakeResp:
    def __init__(self, text: str):
        self.text = text


class FakeHttp:
    def __init__(self, text: str):
        self._text = text

    def get(self, url: str) -> FakeResp:
        return FakeResp(self._text)


NETWORK_PAGE = """
<div class="entry">
  <span class="venue">@ The Showbox</span>
  <h3><a href="/events/detail/1">Band A</a></h3>
  <span class="date">Tue, Jul 7, 2026</span>
</div>
<div class="entry">
  <span class="venue">@ Showbox SoDo</span>
  <h3><a href="/events/detail/2">Band B</a></h3>
  <span class="date">Wed, Jul 8, 2026</span>
</div>
<div class="entry">
  <span class="venue">@ Wonder Ballroom</span>
  <h3><a href="/events/detail/3">Band C</a></h3>
  <span class="date">Thu, Jul 9, 2026</span>
</div>
"""


def make_adapter(config_extra=None, page=NETWORK_PAGE):
    config = {
        "page_url": "https://example.com/events",
        "base_url": "https://example.com",
        "selectors": {
            "item": "div.entry",
            "title": "h3 a",
            "date": "span.date",
            "url": "h3 a",
            "venue": "span.venue",
        },
        **(config_extra or {}),
    }
    return HTMLAdapter("test", config, FakeHttp(page))


def test_venue_map_routes_and_drops_out_of_network():
    events = make_adapter({
        "venue_map": {"The Showbox": "the-showbox", "Showbox SoDo": "showbox-sodo"},
    }).fetch()
    assert [(e.title, e.venue_slug) for e in events] == [
        ("Band A", "the-showbox"),
        ("Band B", "showbox-sodo"),
    ]


def test_venue_map_default_slug_keeps_unmatched():
    events = make_adapter({
        "venue_map": {"The Showbox": "the-showbox"},
        "default_venue_slug": "catch-all",
    }).fetch()
    assert [e.venue_slug for e in events] == ["the-showbox", "catch-all", "catch-all"]


def test_single_venue_ignores_venue_map_machinery():
    events = make_adapter({"venue_slug": "the-showbox"}).fetch()
    assert len(events) == 3
    assert {e.venue_slug for e in events} == {"the-showbox"}
    assert events[0].source_url == "https://example.com/events/detail/1"


SPAN_DATE_PAGE = """
<div class="entry">
  <span class="venue">@ X</span>
  <h3><a href="/e/1">Split Spans</a></h3>
  <span class="date"><span>Mon</span><span>Jul</span><span>06</span><span>2026</span></span>
</div>
"""


def test_sibling_spans_join_with_spaces():
    events = make_adapter({"venue_slug": "x"}, page=SPAN_DATE_PAGE).fetch()
    assert events[0].starts_at is not None
    assert events[0].starts_at.date().isoformat() == "2026-07-06"


def test_parse_event_date_plain():
    assert parse_event_date("Tue, Jul 7, 2026").date().isoformat() == "2026-07-07"


def test_parse_event_date_range_with_trailing_year():
    # "24" must not be mistaken for the year 2024.
    assert parse_event_date("Jul 20 - 24, 2026").date().isoformat() == "2026-07-20"


def test_parse_event_date_cross_month_range_without_year():
    d = parse_event_date("July 07 - August 05")
    assert d is not None and (d.month, d.day) == (7, 7)


def test_parse_event_date_time_with_at_symbol():
    d = parse_event_date("Jul 7 @ 08:00 PM")
    assert (d.month, d.day, d.hour) == (7, 7, 20)


def test_parse_event_date_garbage_returns_none():
    assert parse_event_date("call the box office") is None
