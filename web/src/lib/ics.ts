// Client-generated iCalendar downloads, one VEVENT per show (SPRINT §2).
// RFC 5545 subset: escaped text, folded lines, UTC datetimes, all-day
// fallback when the source only has a date.
import { SITE_URL } from "./seo";
import { eventPath, slugify } from "./routes";
import type { EventRow } from "./types";

const DEFAULT_DURATION_MS = 2 * 60 * 60 * 1000; // assume 2h when no end time

const escText = (s: string) =>
  s.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");

const utcStamp = (iso: string) =>
  new Date(iso).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");

// RFC 5545 §3.1 — content lines ≤75 octets, continuations start with a space.
function fold(line: string): string {
  const out: string[] = [];
  let rest = line;
  while (rest.length > 74) {
    out.push(rest.slice(0, 74));
    rest = " " + rest.slice(74);
  }
  out.push(rest);
  return out.join("\r\n");
}

export function eventIcs(e: EventRow): string {
  const url = `${SITE_URL}${eventPath(e)}`;
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//PNW Stage//pnw-stage.pages.dev//EN",
    "BEGIN:VEVENT",
    `UID:event-${e.id}@pnw-stage.pages.dev`,
    `DTSTAMP:${utcStamp(new Date().toISOString())}`
  ];
  if (e.starts_at) {
    lines.push(`DTSTART:${utcStamp(e.starts_at)}`);
    const end =
      e.ends_at ?? new Date(new Date(e.starts_at).getTime() + DEFAULT_DURATION_MS).toISOString();
    lines.push(`DTEND:${utcStamp(end)}`);
  } else {
    // Date-only listing → all-day event (DTEND is exclusive).
    const next = new Date(Date.parse(`${e.date_local}T00:00:00Z`) + 86_400_000)
      .toISOString()
      .slice(0, 10);
    lines.push(
      `DTSTART;VALUE=DATE:${e.date_local.replace(/-/g, "")}`,
      `DTEND;VALUE=DATE:${next.replace(/-/g, "")}`
    );
  }
  lines.push(
    `SUMMARY:${escText(e.headliner ?? e.title)}`,
    `LOCATION:${escText([e.venue_name, e.city, e.state].filter(Boolean).join(", "))}`,
    `DESCRIPTION:${escText(
      [e.ticket_url && `Tickets: ${e.ticket_url}`, url].filter(Boolean).join("\n")
    )}`,
    `URL:${url}`,
    "END:VEVENT",
    "END:VCALENDAR"
  );
  return lines.map(fold).join("\r\n") + "\r\n";
}

export function downloadIcs(e: EventRow): void {
  const blob = new Blob([eventIcs(e)], { type: "text/calendar;charset=utf-8" });
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = `${slugify(e.headliner ?? e.title)}.ics`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(href);
}
