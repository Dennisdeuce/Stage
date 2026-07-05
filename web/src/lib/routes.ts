// Path-based deep links for events and venues (ORGANIC_GROWTH_SPRINT_v2 §1.2).
// Cloudflare Pages serves prerendered stubs at these paths when they exist and
// falls back to the SPA shell otherwise; either way the app resolves the path
// on load and opens the matching drawer/tab.
// NOTE: slugify is mirrored in scripts/prerender.mjs — keep the two in sync.
import type { EventRow } from "./types";

export function slugify(s: string): string {
  return (
    s
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "event"
  );
}

export function eventPath(e: Pick<EventRow, "id" | "title">): string {
  return `/e/${e.id}-${slugify(e.title)}`;
}

export function venuePath(slug: string): string {
  return `/v/${slug}`;
}

export type DeepLink = { kind: "event"; id: number } | { kind: "venue"; slug: string };

export function parsePath(pathname: string): DeepLink | null {
  const e = pathname.match(/^\/e\/(\d+)(?:-[^/]*)?\/?$/);
  if (e) return { kind: "event", id: Number(e[1]) };
  const v = pathname.match(/^\/v\/([a-z0-9][a-z0-9-]*)\/?$/i);
  if (v) return { kind: "venue", slug: v[1].toLowerCase() };
  return null;
}
