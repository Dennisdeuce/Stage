// Embeddable "upcoming shows" widget (ORGANIC_GROWTH_SPRINT_v2 §3).
// Deliberately tiny: no React, no supabase-js — one PostgREST fetch against
// the same anon read-only views the app uses. Venue sites iframe this page:
//
//   <iframe src="https://pnw-stage.pages.dev/embed.html?venue=<venue_slug>"
//           width="100%" height="420" style="border:0" loading="lazy"
//           title="Upcoming shows — PNW Stage"></iframe>
//
// Params: venue=<slug> · metro=<name> · cat=music|comedy|arts|other
//         limit=<n, default 10, max 25> · theme=dark|light
import { SITE_URL } from "./lib/seo";
import { eventPath } from "./lib/routes";

type Ev = {
  id: number;
  title: string;
  headliner: string | null;
  date_local: string;
  status: string;
  venue_name: string;
  city: string | null;
};

const params = new URLSearchParams(location.search);
if (params.get("theme") === "light") document.documentElement.dataset.theme = "light";

const list = document.getElementById("list")!;

function note(text: string) {
  list.insertAdjacentHTML("beforeend", `<p class="empty"></p>`);
  (list.lastElementChild as HTMLElement).textContent = text;
}

function fmtDate(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric"
  });
}

async function main() {
  const base = import.meta.env.VITE_SUPABASE_URL as string | undefined;
  const key = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;
  if (!base || !key) return note("Widget is not configured.");

  const q = new URLSearchParams({
    select: "id,title,headliner,date_local,status,venue_name,city",
    order: "date_local.asc"
  });
  const venue = params.get("venue");
  const metro = params.get("metro");
  const cat = params.get("cat");
  if (venue) q.set("venue_slug", `eq.${venue}`);
  if (metro) q.set("metro", `eq.${metro}`);
  if (cat) q.set("category", `eq.${cat}`);
  q.set("limit", String(Math.min(Math.max(Number(params.get("limit")) || 10, 1), 25)));

  let events: Ev[];
  try {
    const res = await fetch(`${base}/rest/v1/public_events?${q}`, {
      headers: { apikey: key, Authorization: `Bearer ${key}` }
    });
    if (!res.ok) throw new Error(String(res.status));
    events = await res.json();
  } catch {
    return note("Couldn’t load shows right now.");
  }
  if (!events.length) return note("No upcoming shows listed.");

  for (const e of events) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.className = "ev";
    a.href = `${SITE_URL}${eventPath(e)}?utm_source=embed`;
    a.target = "_blank";
    a.rel = "noopener";

    const d = document.createElement("span");
    d.className = "d";
    d.textContent = fmtDate(e.date_local);

    const body = document.createElement("span");
    const t = document.createElement("span");
    t.className = "t";
    t.textContent = e.headliner ?? e.title;
    body.appendChild(t);
    if (!venue) {
      const v = document.createElement("span");
      v.className = "v";
      v.textContent = ` · ${e.venue_name}${e.city ? `, ${e.city}` : ""}`;
      body.appendChild(v);
    }
    if (e.status === "sold_out") {
      const s = document.createElement("span");
      s.className = "soldout";
      s.textContent = " sold out";
      body.appendChild(s);
    }

    a.append(d, body);
    li.appendChild(a);
    list.appendChild(li);
  }
}

main();
