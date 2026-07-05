// Build-time prerender (ORGANIC_GROWTH_SPRINT_v2 §1.2). Runs after `vite build`
// in the deploy workflow: pulls the public event inventory from Supabase (anon,
// read-only), then writes per-event and per-venue HTML stubs into dist/ so
// non-JS crawlers and link unfurlers get real titles/descriptions/OG/JSON-LD.
// The stubs are the built SPA shell with the <head> rewritten; the app itself
// resolves the path on load and opens the right drawer.
//
// Also regenerates dist/sitemap.xml from the same data.
//
// Zero deps (global fetch, node:fs). Skips gracefully — a missing env or a
// fetch failure must never break a deploy, it just means no stubs this round.
//
// Usage: node scripts/prerender.mjs [distDir=dist]
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { join } from "node:path";

const SITE_URL = "https://pnw-stage.pages.dev";
const DIST = process.argv[2] ?? "dist";

const SUPA_URL = process.env.VITE_SUPABASE_URL;
const SUPA_KEY = process.env.VITE_SUPABASE_ANON_KEY;

// Mirrors src/lib/routes.ts `slugify` — keep the two in sync.
function slugify(s) {
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

const esc = (s) =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function setTitle(html, title) {
  return html.replace(/<title>[^<]*<\/title>/, `<title>${esc(title)}</title>`);
}
function setMeta(html, attr, key, content) {
  const re = new RegExp(`(<meta ${attr}="${key}" content=")[^"]*(")`, "g");
  return html.replace(re, `$1${esc(content)}$2`);
}
function setCanonical(html, url) {
  return html.replace(/(<link rel="canonical" href=")[^"]*(")/, `$1${esc(url)}$2`);
}
function addJsonLd(html, obj) {
  return html.replace("</head>", `<script type="application/ld+json">${JSON.stringify(obj)}</script>\n</head>`);
}

function stub(template, { title, description, url, image, jsonLd }) {
  let html = setTitle(template, title);
  html = setCanonical(html, url);
  html = setMeta(html, "name", "description", description);
  for (const k of ["og:title", "twitter:title"]) html = setMeta(html, k.startsWith("og") ? "property" : "name", k, title);
  for (const k of ["og:description", "twitter:description"]) html = setMeta(html, k.startsWith("og") ? "property" : "name", k, description);
  html = setMeta(html, "property", "og:url", url);
  if (image) {
    html = setMeta(html, "property", "og:image", image);
    html = setMeta(html, "name", "twitter:image", image);
  }
  if (jsonLd) html = addJsonLd(html, jsonLd);
  return html;
}

function writeStub(path, html) {
  const dir = join(DIST, path);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "index.html"), html);
}

const TYPE_BY_CATEGORY = { music: "MusicEvent", comedy: "ComedyEvent", arts: "TheaterEvent", other: "Event" };

function eventJsonLd(e) {
  const item = {
    "@context": "https://schema.org",
    "@type": TYPE_BY_CATEGORY[e.category] ?? "Event",
    name: e.title,
    startDate: e.starts_at ?? e.date_local,
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    location: {
      "@type": "Place",
      name: e.venue_name,
      address: [e.city, e.state].filter(Boolean).join(", ") || e.metro
    }
  };
  if (e.image_url) item.image = e.image_url;
  if (e.headliner) item.performer = { "@type": "PerformingGroup", name: e.headliner };
  if (e.ticket_url) {
    item.offers = {
      "@type": "Offer",
      url: e.ticket_url,
      availability: e.status === "sold_out" ? "https://schema.org/SoldOut" : "https://schema.org/InStock",
      ...(e.price_min != null && { price: e.price_min, priceCurrency: e.currency })
    };
  }
  return item;
}

// RSS 2.0 feed of shows first seen in the last 7 days (SPRINT §2). Refreshed
// on every deploy — the scrape workflow triggers one nightly.
function rss(events) {
  const cutoff = Date.now() - 7 * 86_400_000;
  const items = events
    .filter((e) => e.first_seen && Date.parse(e.first_seen) >= cutoff)
    .sort((a, b) => Date.parse(b.first_seen) - Date.parse(a.first_seen))
    .slice(0, 100)
    .map((e) => {
      const url = `${SITE_URL}/e/${e.id}-${slugify(e.title)}`;
      const bits = [
        `${e.category} at ${e.venue_name}${e.city ? `, ${e.city}` : ""} on ${e.date_local}.`,
        e.ticket_url ? "Primary ticket link on the event page." : null
      ].filter(Boolean);
      return [
        "    <item>",
        `      <title>${esc(`${e.headliner ?? e.title} at ${e.venue_name} — ${e.date_local}`)}</title>`,
        `      <link>${esc(url)}</link>`,
        `      <guid isPermaLink="true">${esc(url)}</guid>`,
        `      <pubDate>${new Date(e.first_seen).toUTCString()}</pubDate>`,
        `      <description>${esc(bits.join(" "))}</description>`,
        "    </item>"
      ].join("\n");
    });
  return [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<rss version="2.0">`,
    `  <channel>`,
    `    <title>PNW Stage — newly announced shows</title>`,
    `    <link>${SITE_URL}/</link>`,
    `    <description>Concerts &amp; comedy just announced across the Pacific Northwest.</description>`,
    `    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>`,
    items.join("\n"),
    `  </channel>`,
    `</rss>`,
    ``
  ].join("\n");
}

function sitemap(urls) {
  const today = new Date().toISOString().slice(0, 10);
  const entries = urls
    .map((u) => `  <url><loc>${esc(u)}</loc><lastmod>${today}</lastmod></url>`)
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${entries}\n</urlset>\n`;
}

async function main() {
  if (!SUPA_URL || !SUPA_KEY) {
    console.warn("prerender: VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY not set — skipping.");
    return;
  }
  const templatePath = join(DIST, "index.html");
  if (!existsSync(templatePath)) {
    console.warn(`prerender: ${templatePath} not found — run the build first. Skipping.`);
    return;
  }
  const template = readFileSync(templatePath, "utf8");

  let events;
  try {
    const res = await fetch(`${SUPA_URL}/rest/v1/public_events?select=*&order=date_local.asc`, {
      headers: { apikey: SUPA_KEY, Authorization: `Bearer ${SUPA_KEY}` }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    events = await res.json();
  } catch (err) {
    console.warn(`prerender: could not fetch events (${err}) — skipping.`);
    return;
  }

  const urls = [`${SITE_URL}/`];

  for (const e of events) {
    const path = `e/${e.id}-${slugify(e.title)}`;
    const url = `${SITE_URL}/${path}`;
    const when = e.date_local ?? "";
    const desc = `${e.title} at ${e.venue_name}${e.city ? `, ${e.city}` : ""} on ${when}. Dates, times & primary ticket links on PNW Stage.`;
    writeStub(
      path,
      stub(template, {
        title: `${e.headliner ?? e.title} at ${e.venue_name} — PNW Stage`,
        description: desc,
        url,
        image: e.image_url || undefined,
        jsonLd: eventJsonLd(e)
      })
    );
    urls.push(url);
  }

  // Venues derived from the same payload — no extra query, always consistent.
  const venues = new Map();
  for (const e of events) {
    const v = venues.get(e.venue_slug) ?? { name: e.venue_name, city: e.city, state: e.state, count: 0 };
    v.count += 1;
    venues.set(e.venue_slug, v);
  }
  for (const [slug, v] of venues) {
    const path = `v/${slug}`;
    const url = `${SITE_URL}/${path}`;
    const where = [v.city, v.state].filter(Boolean).join(", ");
    writeStub(
      path,
      stub(template, {
        title: `${v.name} — upcoming shows — PNW Stage`,
        description: `Upcoming concerts & comedy at ${v.name}${where ? `, ${where}` : ""} — ${v.count} listed. Dates & primary ticket links on PNW Stage.`,
        url,
        jsonLd: {
          "@context": "https://schema.org",
          "@type": "Place",
          name: v.name,
          ...(where && { address: where })
        }
      })
    );
    urls.push(url);
  }

  writeFileSync(join(DIST, "sitemap.xml"), sitemap(urls));
  writeFileSync(join(DIST, "feed.xml"), rss(events));
  console.log(`prerender: wrote ${events.length} event + ${venues.size} venue stubs, sitemap with ${urls.length} URLs, RSS feed.`);
}

await main();
