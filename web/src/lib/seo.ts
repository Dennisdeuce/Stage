// Runtime structured data + titles (ORGANIC_GROWTH_SPRINT_v2 §1.1).
// The site is a single-URL SPA, so event JSON-LD is injected client-side;
// JS-executing crawlers (Googlebot) see the live inventory this way.
import type { EventRow } from "./types";

export const SITE_URL = "https://pnw-stage.pages.dev";
export const SITE_NAME = "PNW Stage";

const JSONLD_ID = "events-jsonld";
const MAX_ITEMS = 50;

const TYPE_BY_CATEGORY: Record<EventRow["category"], string> = {
  music: "MusicEvent",
  comedy: "ComedyEvent",
  arts: "TheaterEvent",
  other: "Event"
};

const STATUS_URL: Partial<Record<EventRow["status"], string>> = {
  cancelled: "https://schema.org/EventCancelled",
  postponed: "https://schema.org/EventPostponed"
};

function eventItem(e: EventRow, position: number) {
  const item: Record<string, unknown> = {
    "@type": TYPE_BY_CATEGORY[e.category],
    name: e.title,
    startDate: e.starts_at ?? e.date_local,
    eventStatus: STATUS_URL[e.status] ?? "https://schema.org/EventScheduled",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    location: {
      "@type": "Place",
      name: e.venue_name,
      address: [e.city, e.state].filter(Boolean).join(", ") || e.metro
    }
  };
  if (e.image_url) item.image = e.image_url;
  if (e.description) item.description = e.description;
  if (e.headliner) item.performer = { "@type": "PerformingGroup", name: e.headliner };
  if (e.ticket_url) {
    item.offers = {
      "@type": "Offer",
      url: e.ticket_url,
      availability:
        e.status === "sold_out" ? "https://schema.org/SoldOut" : "https://schema.org/InStock",
      ...(e.price_min != null && { price: e.price_min, priceCurrency: e.currency })
    };
  }
  return { "@type": "ListItem", position, item };
}

/** Replace the <head> JSON-LD block with an ItemList of the given events. */
export function injectEventJsonLd(events: EventRow[]) {
  document.getElementById(JSONLD_ID)?.remove();
  if (!events.length) return;
  const script = document.createElement("script");
  script.type = "application/ld+json";
  script.id = JSONLD_ID;
  script.text = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "ItemList",
    itemListElement: events.slice(0, MAX_ITEMS).map((e, i) => eventItem(e, i + 1))
  });
  document.head.appendChild(script);
}

const TAB_TITLES: Record<string, string> = {
  feed: `${SITE_NAME} — Concerts & Comedy`,
  calendar: `Calendar — ${SITE_NAME}`,
  venues: `Venues — ${SITE_NAME}`
};

export function titleForTab(tab: string): string {
  return TAB_TITLES[tab] ?? TAB_TITLES.feed;
}
