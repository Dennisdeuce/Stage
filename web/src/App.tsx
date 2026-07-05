import { useEffect, useMemo, useState } from "react";
import { MarqueeHeader, type Tab } from "./components/MarqueeHeader";
import { FeedView } from "./components/FeedView";
import { CalendarView } from "./components/CalendarView";
import { VenuesView } from "./components/VenuesView";
import { FilterDrawer } from "./components/FilterDrawer";
import { EventDrawer } from "./components/EventDrawer";
import { useEvents } from "./lib/useEvents";
import { readLastVisit, writeLastVisit, isNewSince } from "./lib/lastVisit";
import {
  ALL_REGIONS,
  filtersFromParams,
  paramsFromFilters,
  matches,
  type Filters
} from "./lib/filters";
import { injectEventJsonLd, titleForTab } from "./lib/seo";
import { parsePath, eventPath } from "./lib/routes";
import type { EventRow } from "./lib/types";

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const deepLink = useMemo(() => parsePath(window.location.pathname), []);
  const [filters, setFilters] = useState<Filters>(() => filtersFromParams(params));
  const [tab, setTab] = useState<Tab>(
    () => (params.get("view") as Tab) || (deepLink?.kind === "venue" ? "venues" : "feed")
  );
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [active, setActive] = useState<EventRow | null>(null);
  // A shared /e/<id>-<slug> link waits for data, then opens the drawer (§1.2).
  const [pendingEventId, setPendingEventId] = useState<number | null>(
    deepLink?.kind === "event" ? deepLink.id : null
  );

  // Capture last-visit BEFORE recording this visit, so the diff is correct (§6.3).
  const [since, setSince] = useState<Date | null>(() => readLastVisit());
  useEffect(() => {
    writeLastVisit(new Date());
  }, []);

  const { events, health, loading, error } = useEvents(filters.showExpandable);

  // Resolve a pending event deep link once data is in. If the event isn't in
  // the core payload it may be an expandable-metro show — reveal those once
  // and let the refreshed `events` re-run this effect.
  useEffect(() => {
    if (pendingEventId == null || loading) return;
    const hit = events.find((e) => e.id === pendingEventId);
    if (hit) {
      setActive(hit);
      setPendingEventId(null);
    } else if (!filters.showExpandable) {
      setFilters((f) => ({ ...f, showExpandable: true }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events, loading, pendingEventId]);

  // Keep the URL in sync (shareable / restorable — §6.6). The open event owns
  // the path (§1.2 deep links); filters/tab live in the query string.
  useEffect(() => {
    if (pendingEventId != null) return; // don't clobber a not-yet-resolved deep link
    const p = paramsFromFilters(filters);
    if (tab !== "feed") p.set("view", tab);
    const qs = p.toString();
    const path = active ? eventPath(active) : "/";
    window.history.replaceState(null, "", qs ? `${path}?${qs}` : path);
  }, [filters, tab, active, pendingEventId]);

  // Structured data reflects the full inventory, not the filter state (§1.1).
  useEffect(() => {
    injectEventJsonLd(events);
  }, [events]);
  useEffect(() => {
    document.title = active
      ? `${active.headliner ?? active.title} at ${active.venue_name} — PNW Stage`
      : titleForTab(tab);
  }, [tab, active]);

  const visible = useMemo(() => events.filter((e) => matches(e, filters)), [events, filters]);
  const isNew = (e: EventRow) => isNewSince(e.first_seen, since);

  const activeFilterCount =
    (filters.categories.length ? 1 : 0) +
    (filters.regions.length !== ALL_REGIONS.length ? 1 : 0) +
    (filters.showExpandable ? 1 : 0) +
    (filters.priceCeiling != null ? 1 : 0) +
    (filters.allAges ? 1 : 0) +
    (filters.freeOnly ? 1 : 0) +
    (filters.hasTickets ? 1 : 0) +
    (filters.sale !== "any" ? 1 : 0) +
    (filters.query ? 1 : 0);

  return (
    <div className="min-h-full pb-20">
      <MarqueeHeader
        tab={tab}
        onTab={setTab}
        onOpenFilters={() => setFiltersOpen(true)}
        activeFilterCount={activeFilterCount}
      />

      <main className="mx-auto max-w-5xl px-4 py-6">
        {error ? (
          <ConfigError message={error} />
        ) : loading ? (
          <Skeletons />
        ) : (
          <>
            {tab === "feed" && (
              <FeedView
                events={visible}
                isNew={isNew}
                onOpen={setActive}
                showExpandable={filters.showExpandable}
                onToggleExpandable={() => setFilters({ ...filters, showExpandable: true })}
                onMarkSeen={() => {
                  const now = new Date();
                  setSince(now);
                  writeLastVisit(now);
                }}
              />
            )}
            {tab === "calendar" && <CalendarView events={visible} onOpen={setActive} />}
            {tab === "venues" && (
              <VenuesView events={visible} health={health} isNew={isNew} onOpen={setActive} />
            )}
          </>
        )}
      </main>

      <FilterDrawer
        open={filtersOpen}
        filters={filters}
        onChange={setFilters}
        onClose={() => setFiltersOpen(false)}
      />
      <EventDrawer event={active} onClose={() => setActive(null)} />

      <footer className="mx-auto max-w-5xl px-4 py-8 text-center font-mono text-[11px] uppercase tracking-widest text-moss">
        Event data via Ticketmaster &amp; venue listings · Primary on-sale links only, never resale
      </footer>
    </div>
  );
}

function Skeletons() {
  return (
    <div className="grid gap-3" aria-busy="true">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-28 animate-pulse rounded-lg bg-ink-800" />
      ))}
    </div>
  );
}

function ConfigError({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-coral/40 bg-coral/5 p-6 text-center">
      <p className="font-display text-2xl tracking-wide text-coral">Can’t load shows</p>
      <p className="mt-2 text-sm text-moss">{message}</p>
    </div>
  );
}
