"""Seed the venue + source registry (BUILD_SPEC §3.3).

Run once after migrations: `python seed_venues.py`. Idempotent — upserts by slug.

Source-type strategy (§3.1): feed-first. Big rooms come through the Ticketmaster
Discovery API (queried by DMA, not per-venue). Clubs/arts/comedy use per-venue
HTML adapters whose CSS selectors live in `source_config.selectors`.

Selector provenance: configs in VERIFIED_SOURCES were validated against the
live sites (2026-07-06, see verify_sources.py) and carry `verified: True`.
Venues NOT in that dict still use best-effort GENERIC_SELECTORS with
`verified: False` — several sites are fully JS-rendered (Dice/VenuePilot/
SeatEngine widgets) and need a JSON endpoint or a headless pass; wrong
selectors simply yield zero events and surface as a red source-health badge —
they never break other adapters (§5.6).

Ticketmaster venue routing: until real `tm_venue_id`s are resolved and cached
(populate `venue_index` in the TM sources / `venues.tm_venue_id`), TM events land
on per-DMA catch-all venues (tm-seattle-tacoma, tm-portland, tm-vancouver-bc).
"""
from __future__ import annotations

import os

# A generic selector template for venue calendar pages. Override per-venue as needed.
GENERIC_SELECTORS = {
    "item": ".event, .eventItem, article.event, li.event",
    "title": ".title, .event-title, h3, h2",
    "date": "time, .date, .event-date",
    "url": "a",
    "image": "img",
    "description": ".description, .summary",
}

# (slug, name, metro, region, city, state, website, source_kind, lat, lng)
VENUES = [
    # ---- Seattle core: STG ----
    ("paramount-theatre", "Paramount Theatre", "seattle", "core", "Seattle", "WA", "https://www.stgpresents.org", "stg", 47.6131, -122.3318),
    ("moore-theatre", "Moore Theatre", "seattle", "core", "Seattle", "WA", "https://www.stgpresents.org", "stg", 47.6109, -122.3417),
    ("neptune-theatre", "Neptune Theatre", "seattle", "core", "Seattle", "WA", "https://www.stgpresents.org", "stg", 47.6615, -122.3138),
    # ---- Seattle core: big rooms via Ticketmaster ----
    ("climate-pledge-arena", "Climate Pledge Arena", "seattle", "core", "Seattle", "WA", "https://www.climatepledgearena.com", "ticketmaster", 47.6221, -122.3540),
    ("wamu-theater", "WaMu Theater", "seattle", "core", "Seattle", "WA", "https://www.wamutheater.com", "ticketmaster", 47.5952, -122.3318),
    ("lumen-field", "Lumen Field & Event Center", "seattle", "core", "Seattle", "WA", "https://www.lumenfield.com", "ticketmaster", 47.5952, -122.3316),
    ("t-mobile-park", "T-Mobile Park", "seattle", "core", "Seattle", "WA", "https://www.mlb.com/mariners/ballpark", "ticketmaster", 47.5914, -122.3325),
    # ---- Seattle core: clubs (HTML) ----
    ("the-showbox", "The Showbox", "seattle", "core", "Seattle", "WA", "https://www.showboxpresents.com", "html", 47.6086, -122.3387),
    ("showbox-sodo", "Showbox SoDo", "seattle", "core", "Seattle", "WA", "https://www.showboxpresents.com", "html", 47.5806, -122.3340),
    ("little-red-hen", "Little Red Hen", "seattle", "core", "Seattle", "WA", "https://www.littleredhen.com", "html", 47.6797, -122.3275),
    ("tractor-tavern", "Tractor Tavern", "seattle", "core", "Seattle", "WA", "https://www.tractortavern.com", "html", 47.6686, -122.3848),
    ("el-corazon", "El Corazón", "seattle", "core", "Seattle", "WA", "https://www.elcorazonseattle.com", "html", 47.6196, -122.3306),
    ("the-crocodile", "The Crocodile", "seattle", "core", "Seattle", "WA", "https://www.thecrocodile.com", "html", 47.6133, -122.3430),
    ("neumos", "Neumos", "seattle", "core", "Seattle", "WA", "https://www.neumos.com", "html", 47.6140, -122.3199),
    ("barboza", "Barboza", "seattle", "core", "Seattle", "WA", "https://www.thebarboza.com", "html", 47.6140, -122.3199),
    ("nectar-lounge", "Nectar Lounge", "seattle", "core", "Seattle", "WA", "https://www.nectarlounge.com", "html", 47.6517, -122.3553),
    ("the-triple-door", "The Triple Door", "seattle", "core", "Seattle", "WA", "https://www.thetripledoor.net", "html", 47.6080, -122.3360),
    ("jazz-alley", "Dimitriou's Jazz Alley", "seattle", "core", "Seattle", "WA", "https://www.jazzalley.com", "html", 47.6157, -122.3360),
    ("benaroya-hall", "Benaroya Hall (Seattle Symphony)", "seattle", "core", "Seattle", "WA", "https://www.seattlesymphony.org", "html", 47.6080, -122.3370),
    ("meany-center", "Meany Center (UW)", "seattle", "core", "Seattle", "WA", "https://www.meanycenter.org", "html", 47.6557, -122.3093),
    ("mccaw-hall", "McCaw Hall", "seattle", "core", "Seattle", "WA", "https://www.mccawhall.com", "html", 47.6248, -122.3499),
    ("the-vera-project", "The Vera Project", "seattle", "core", "Seattle", "WA", "https://www.theveraproject.org", "html", 47.6244, -122.3543),
    # ---- Comedy ----
    ("comedy-underground", "Comedy Underground", "seattle", "core", "Seattle", "WA", "https://www.comedyunderground.com", "html", 47.6010, -122.3340),
    ("jet-city-improv", "Jet City Improv", "seattle", "core", "Seattle", "WA", "https://www.jetcityimprov.org", "html", 47.6628, -122.3215),
    ("tacoma-comedy-club", "Tacoma Comedy Club", "tacoma", "south", "Tacoma", "WA", "https://www.tacomacomedyclub.com", "html", 47.2510, -122.4410),
    ("parlor-live-bellevue", "Parlor Live (Bellevue)", "seattle", "eastside", "Bellevue", "WA", "https://bellevue.parlorlive.com", "html", 47.6160, -122.2010),
    ("laughs-comedy-kirkland", "Laughs Comedy Club (Kirkland)", "seattle", "eastside", "Kirkland", "WA", "https://www.laughscomedy.com", "html", 47.6800, -122.2080),
    # ---- South / Eastside big rooms (TM) ----
    ("tacoma-dome", "Tacoma Dome", "tacoma", "south", "Tacoma", "WA", "https://www.tacomadome.org", "ticketmaster", 47.2366, -122.4267),
    ("white-river-amphitheatre", "White River Amphitheatre", "tacoma", "south", "Auburn", "WA", "https://www.whiteriveramphitheatre.com", "ticketmaster", 47.2230, -122.0680),
    ("showare-center", "accesso ShoWare Center", "tacoma", "south", "Kent", "WA", "https://www.showarecenter.com", "ticketmaster", 47.3810, -122.2470),
    ("marymoor-park", "Marymoor Park", "seattle", "eastside", "Redmond", "WA", "https://www.marymoorconcerts.com", "ticketmaster", 47.6580, -122.1180),
    ("emerald-queen-casino", "Emerald Queen Casino", "tacoma", "south", "Tacoma", "WA", "https://www.emeraldqueen.com", "ticketmaster", 47.2090, -122.4360),
    ("chateau-ste-michelle", "Chateau Ste. Michelle", "seattle", "eastside", "Woodinville", "WA", "https://www.ste-michelle.com", "ticketmaster", 47.7350, -122.1620),
    # ---- South / Eastside arts (HTML) ----
    ("pantages-theater", "Pantages Theater (Tacoma Arts Live)", "tacoma", "south", "Tacoma", "WA", "https://www.tacomaartslive.org", "html", 47.2530, -122.4400),
    ("temple-theatre", "Temple Theatre", "tacoma", "south", "Tacoma", "WA", "https://www.templetheater.com", "html", 47.2530, -122.4380),
    ("mcmenamins-elks-temple", "McMenamins Elks Temple / Spanish Ballroom", "tacoma", "south", "Tacoma", "WA", "https://www.mcmenamins.com", "html", 47.2520, -122.4390),
    # ---- North toward Bellingham ----
    ("tulalip-resort-casino", "Tulalip Resort Casino", "everett", "north", "Tulalip", "WA", "https://www.tulalipresortcasino.com", "ticketmaster", 48.0620, -122.1810),
    ("angel-of-the-winds-arena", "Angel of the Winds Arena", "everett", "north", "Everett", "WA", "https://www.angelofthewindsarena.com", "ticketmaster", 47.9770, -122.2030),
    ("skagit-valley-casino", "Skagit Valley Casino Resort", "bellingham", "north", "Bow", "WA", "https://www.theskagit.com", "ticketmaster", 48.5760, -122.3110),
    ("edmonds-center-arts", "Edmonds Center for the Arts", "everett", "north", "Edmonds", "WA", "https://www.ec4arts.org", "html", 47.8110, -122.3770),
    ("mount-baker-theatre", "Mount Baker Theatre", "bellingham", "north", "Bellingham", "WA", "https://www.mountbakertheatre.com", "html", 48.7510, -122.4790),
    ("wild-buffalo", "Wild Buffalo House of Music", "bellingham", "north", "Bellingham", "WA", "https://www.wildbuffalo.net", "html", 48.7520, -122.4780),
    # ---- Expandable: Portland ----
    ("moda-center", "Moda Center", "portland", "expandable", "Portland", "OR", "https://www.rosequarter.com", "ticketmaster", 45.5316, -122.6668),
    ("keller-auditorium", "Keller Auditorium", "portland", "expandable", "Portland", "OR", "https://www.portland5.com", "ticketmaster", 45.5120, -122.6790),
    ("arlene-schnitzer", "Arlene Schnitzer Concert Hall", "portland", "expandable", "Portland", "OR", "https://www.portland5.com", "ticketmaster", 45.5180, -122.6820),
    ("roseland-theater", "Roseland Theater", "portland", "expandable", "Portland", "OR", "https://www.roselandpdx.com", "html", 45.5270, -122.6760),
    ("crystal-ballroom", "Crystal Ballroom", "portland", "expandable", "Portland", "OR", "https://www.crystalballroompdx.com", "html", 45.5220, -122.6850),
    ("aladdin-theater", "Aladdin Theater", "portland", "expandable", "Portland", "OR", "https://www.aladdin-theater.com", "html", 45.4970, -122.6540),
    ("revolution-hall", "Revolution Hall", "portland", "expandable", "Portland", "OR", "https://www.revolutionhall.com", "html", 45.5180, -122.6360),
    ("helium-comedy-portland", "Helium Comedy Club (Portland)", "portland", "expandable", "Portland", "OR", "https://portland.heliumcomedy.com", "html", 45.5050, -122.6610),
    # ---- Expandable: Vancouver WA ----
    ("ilani-casino", "ilani Casino Resort", "vancouver_wa", "expandable", "Ridgefield", "WA", "https://www.ilaniresort.com", "html", 45.8470, -122.7350),
    ("rv-inn-amphitheater", "RV Inn Style Resorts Amphitheater", "vancouver_wa", "expandable", "Ridgefield", "WA", "https://www.rvinnstyleamp.com", "ticketmaster", 45.8330, -122.7270),
    # ---- Expandable: Vancouver BC ----
    ("rogers-arena", "Rogers Arena", "vancouver_bc", "expandable", "Vancouver", "BC", "https://www.rogersarena.com", "ticketmaster", 49.2778, -123.1089),
    ("commodore-ballroom", "Commodore Ballroom", "vancouver_bc", "expandable", "Vancouver", "BC", "https://www.commodoreballroom.com", "ticketmaster", 49.2810, -123.1230),
    ("orpheum-vancouver", "Orpheum Theatre", "vancouver_bc", "expandable", "Vancouver", "BC", "https://www.vancouvercivictheatres.com", "html", 49.2800, -123.1210),
    ("vogue-theatre", "Vogue Theatre", "vancouver_bc", "expandable", "Vancouver", "BC", "https://www.voguetheatre.com", "html", 49.2810, -123.1200),
    ("yuk-yuks-vancouver", "Yuk Yuk's (Vancouver)", "vancouver_bc", "expandable", "Vancouver", "BC", "https://www.yukyuks.com", "html", 49.2820, -123.1180),
    # ---- Ticketmaster per-DMA catch-all venues (until tm_venue_id mapping is resolved) ----
    ("tm-seattle-tacoma", "Other Seattle–Tacoma venues (Ticketmaster)", "seattle", "core", "Seattle", "WA", "https://www.ticketmaster.com", "ticketmaster", None, None),
    ("tm-portland", "Other Portland venues (Ticketmaster)", "portland", "expandable", "Portland", "OR", "https://www.ticketmaster.com", "ticketmaster", None, None),
    ("tm-vancouver-bc", "Other Vancouver BC venues (Ticketmaster)", "vancouver_bc", "expandable", "Vancouver", "BC", "https://www.ticketmaster.ca", "ticketmaster", None, None),
]


def venue_rows() -> list[dict]:
    rows = []
    for slug, name, metro, region, city, state, website, kind, lat, lng in VENUES:
        rows.append({
            "slug": slug,
            "name": name,
            "metro": metro,
            "region": region,
            "city": city,
            "state": state,
            "country": "CA" if state == "BC" else "US",
            "lat": lat,
            "lng": lng,
            "website": website,
            "source_kind": kind,
            "is_active": True,
            "source_config": {},
        })
    return rows


# Live-validated per-venue source configs (see module docstring). Keyed by
# venue slug; `kind` defaults to "html". Venues listed here are excluded from
# the generic fallback loop. Re-validate with: python verify_sources.py
VERIFIED_SOURCES: dict[str, dict] = {
    "tractor-tavern": {
        "page_url": "https://tractortavern.com/calendar/",
        "selectors": {
            "item": "div.flexmedia--artistevents",
            "title": ".artisteventsname",
            "date": ".artisteventstime",
            "url": ".eventinfo a",
        },
    },
    "nectar-lounge": {
        "page_url": "https://nectarlounge.com/events/calendar/",
        "selectors": {
            "item": "div.sg-events__event",
            "title": ".sg-events__event-title",
            "date": "time.sg-events__event-date",
            "url": ".sg-events__event-title-link",
            "image": ".sg-events__event-featured-image",
        },
    },
    "neumos": {
        "page_url": "https://www.neumos.com/events",
        "date_attr": "aria-label",
        "selectors": {
            "item": "div.eventItem",
            "title": "h3.title",
            "date": ".date",
            "url": "h3.title a",
            "image": ".thumb img",
        },
    },
    "barboza": {
        "page_url": "https://www.thebarboza.com/events",
        "date_attr": "aria-label",
        "selectors": {
            "item": "div.eventItem",
            "title": "h3.title",
            "date": ".date",
            "url": "h3.title a",
            "image": ".thumb img",
        },
    },
    "mccaw-hall": {
        "page_url": "https://www.mccawhall.com/events",
        "selectors": {
            "item": "div.entry",
            "title": ".info h3",
            "date": ".date",
            "url": ".info h3 a",
            "image": ".thumb img",
        },
    },
    "el-corazon": {
        # Server-rendered Webflow list; covers both rooms (El Corazón + Funhouse).
        "page_url": "https://www.elcorazonseattle.com/",
        "selectors": {
            "item": "div.event-div",
            "title": ".headliners",
            "date": ".day-date",
            "url": "a.opendate",
            "image": ".show-image-wrapper img",
        },
    },
    "the-crocodile": {
        "page_url": "https://calendar.thecrocodile.com/",
        "selectors": {
            "item": "div.uui-layout88_item.w-dyn-item",
            "title": "h3.uui-heading-xxsmall-2",
            "date": ".cal-start-date",
            "url": "a",
            "image": ".show-image-wrapper img",
        },
    },
    "aladdin-theater": {
        # Etix-powered; the meta[itemprop=startDate] mislabels local time as
        # UTC, so read the human date instead (date-only, no bogus hour).
        "page_url": "https://www.aladdin-theater.com/",
        "selectors": {
            "item": "div.event.event--list-style",
            "title": "h3.event-title",
            "date": ".event-date--full",
            "url": "a.event-action",
            "image": ".event-image img",
        },
    },
    "mount-baker-theatre": {
        "page_url": "https://www.mountbakertheatre.com/events-tickets/",
        "selectors": {
            "item": "div.c-col-card--event",
            "title": "h3.c-col-title",
            "date": ".c-col-card__time",
            "url": "a.c-col-card__link",
        },
    },
    "helium-comedy-portland": {
        "page_url": "https://portland.heliumcomedy.com/events",
        "selectors": {
            "item": "div.event-expand-toggle",
            "title": "h3.el-header",
            "date": ".el-date-range",
            "url": "h3.el-header a",
            "image": ".el-image img",
        },
    },
    "pantages-theater": {
        # Tacoma Arts Live's calendar (Modern Events Calendar) spans their
        # rooms (Pantages/Rialto/Armory); all map to this org venue for now.
        "page_url": "https://www.tacomaartslive.org/upcoming-events/",
        "selectors": {
            "item": "article.mec-event-article",
            "title": ".mec-event-title",
            "date": ".mec-start-date-label",
            "url": ".mec-event-title a",
            "image": ".mec-event-image img",
        },
    },
    "ilani-casino": {
        # Date tiles carry no year; dateutil assumes the current year, which
        # holds for this near-term schedule page.
        "page_url": "https://ilaniresort.com/events-and-promotions/schedule-of-events/",
        "selectors": {
            "item": "div.event.my-3",
            "title": ".calendar-tile-title",
            "date": ".events-date-tile-view",
            "url": "a",
            "image": "img",
        },
    },
    # WordPress "The Events Calendar" sites — use their JSON API, not HTML.
    "crystal-ballroom": {
        "kind": "json",
        "feed_url": "https://www.crystalballroompdx.com/wp-json/tribe/events/v1/events?per_page=50",
        "items_path": "events",
        "map": {
            "title": "title",
            "starts_at": "start_date",
            "description": "excerpt",
            "image_url": "image.url",
            "source_url": "url",
            "ticket_url": "website",
        },
    },
    "laughs-comedy-kirkland": {
        "kind": "json",
        "feed_url": "https://laughscomedyclub.com/wp-json/tribe/events/v1/events?per_page=50",
        "items_path": "events",
        "map": {
            "title": "title",
            "starts_at": "start_date",
            "description": "excerpt",
            "image_url": "image.url",
            "source_url": "url",
            "ticket_url": "website",
        },
    },
}

# Venues fed by the shared showboxpresents source below, not per-venue rows.
MULTI_VENUE_SOURCED = {"the-showbox", "showbox-sodo"}


def source_rows() -> list[dict]:
    """One source per adapter. STG = 1 source for 3 venues; TM = per-DMA."""
    sources: list[dict] = []

    # STG (Paramount/Moore/Neptune) — feed-first, scrape fallback.
    sources.append({
        "slug": "stg",
        "kind": "stg",
        "is_active": True,
        "config": {
            "page_url": "https://www.stgpresents.org/tickets/calendar",
            "base_url": "https://www.stgpresents.org",
            "default_venue_slug": "paramount-theatre",
            "source_priority": 10,
            "venue_map": {
                "Paramount": "paramount-theatre",
                "Moore": "moore-theatre",
                "Neptune": "neptune-theatre",
            },
            "selectors": {
                "item": ".calendar-item, .event",
                "title": ".title, h3",
                "date": "time, .date",
                "url": "a",
                "venue": ".venue, .location",
            },
            "verified": False,
        },
    })

    # Ticketmaster — Seattle/Tacoma DMA 819, Portland DMA 820, Vancouver BC by geo.
    sources.append({
        "slug": "ticketmaster_seatac",
        "kind": "ticketmaster",
        "is_active": True,
        "config": {
            "dma_id": 819,
            "classifications": ["music", "comedy", "arts & theatre"],
            "fallback_venue_slug": "tm-seattle-tacoma",
            "source_priority": 50,
            "venue_index": {},  # populate tm_venue_id -> venue_slug to route big rooms
            "tz": "America/Los_Angeles",
        },
    })
    sources.append({
        "slug": "ticketmaster_portland",
        "kind": "ticketmaster",
        "is_active": True,
        "config": {
            "dma_id": 820,
            "classifications": ["music", "comedy", "arts & theatre"],
            "fallback_venue_slug": "tm-portland",
            "source_priority": 50,
            "venue_index": {},
            "tz": "America/Los_Angeles",
        },
    })
    sources.append({
        "slug": "ticketmaster_vancouver_bc",
        "kind": "ticketmaster",
        "is_active": True,
        "config": {
            "geo_point": "49.2827,-123.1207",
            "radius": 25,
            "classifications": ["music", "comedy"],
            "fallback_venue_slug": "tm-vancouver-bc",
            "source_priority": 50,
            "venue_index": {},
            "tz": "America/Vancouver",
        },
    })

    # Showbox Presents lists its whole AEG network on one page; route rooms by
    # the item's venue line and drop out-of-town entries (validated live).
    sources.append({
        "slug": "showboxpresents",
        "kind": "html",
        "is_active": True,
        "config": {
            "page_url": "https://www.showboxpresents.com/events/all",
            "base_url": "https://www.showboxpresents.com",
            "source_priority": 10,
            "venue_map": {
                "The Showbox": "the-showbox",
                "Showbox SoDo": "showbox-sodo",
            },
            "selectors": {
                "item": "div.entry.showboxpresents",
                "title": "h3 a",
                "date": "span.date",
                "url": ".title h3 a",
                "image": ".thumb img",
                "venue": "span.venue",
            },
            "verified": True,
        },
    })

    # Per-venue sources for every html venue: live-validated config when we
    # have one, generic best-effort selectors otherwise.
    html_venues = [(slug, website) for slug, _n, _m, _r, _c, _s, website, kind, *_ in VENUES if kind == "html"]
    for slug, website in html_venues:
        if slug in MULTI_VENUE_SOURCED:
            continue
        override = VERIFIED_SOURCES.get(slug)
        if override:
            kind = override.get("kind", "html")
            config: dict = {
                "venue_slug": slug,
                "source_priority": 10,  # venue feed beats TM
                "verified": True,
                **{k: v for k, v in override.items() if k != "kind"},
            }
            if kind == "html":
                config.setdefault("base_url", website)
        else:
            kind = "html"
            config = {
                "venue_slug": slug,
                "page_url": website,           # TODO: point at the actual calendar path
                "base_url": website,
                "source_priority": 10,
                "selectors": GENERIC_SELECTORS,
                "verified": False,
            }
        sources.append({"slug": slug, "kind": kind, "is_active": True, "config": config})
    return sources


def main() -> None:
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not (url and key):
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY. See README.")
    client = create_client(url, key)

    venues = venue_rows()
    sources = source_rows()
    client.table("venues").upsert(venues, on_conflict="slug").execute()
    client.table("sources").upsert(sources, on_conflict="slug").execute()
    print(f"Seeded {len(venues)} venues and {len(sources)} sources.")


if __name__ == "__main__":
    main()
