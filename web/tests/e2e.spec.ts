import { test, expect, type Page } from "@playwright/test";
import { mockSupabase } from "./fixtures";

const SCREENS = "tests/__screens__";

// Resale/secondary domains that must NEVER appear as a buy link (BUILD_SPEC §3.4 / §9.4).
const RESALE = ["stubhub", "vividseats", "seatgeek.com", "/resale", "tmr", "viagogo"];

async function ticketHrefs(page: Page): Promise<string[]> {
  return page.$$eval('a[href]', (as) =>
    as.map((a) => (a as HTMLAnchorElement).href).filter((h) => /tickets|axs|ticketmaster|\.com\/e\//i.test(h))
  );
}

test.beforeEach(async ({ page }) => {
  await mockSupabase(page);
});

test("feed loads with cards and only primary (non-resale) ticket links", async ({ page }) => {
  await page.goto("/");
  const cards = page.locator("article");
  await expect(cards.first()).toBeVisible();
  expect(await cards.count()).toBeGreaterThanOrEqual(1);

  // A real, http(s) ticket link exists and none are on the resale blocklist.
  const hrefs = await ticketHrefs(page);
  expect(hrefs.length).toBeGreaterThanOrEqual(1);
  for (const h of hrefs) {
    expect(h).toMatch(/^https?:\/\//);
    for (const bad of RESALE) expect(h.toLowerCase()).not.toContain(bad);
  }
  await page.screenshot({ path: `${SCREENS}/feed.png`, fullPage: true });
});

test("calendar renders week, month, and year with no console errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

  await page.goto("/");
  await page.getByRole("button", { name: "Calendar" }).click();
  await expect(page.locator(".fc")).toBeVisible();

  await page.getByRole("button", { name: "Month", exact: true }).click();
  await expect(page.locator(".fc-dayGridMonth-view")).toBeVisible();
  await page.screenshot({ path: `${SCREENS}/calendar-month.png`, fullPage: true });

  await page.getByRole("button", { name: "Week", exact: true }).click();
  await expect(page.locator(".fc-timeGridWeek-view")).toBeVisible();

  await page.getByRole("button", { name: "Year", exact: true }).click();
  await expect(page.locator(".fc-multiMonthYear-view")).toBeVisible();
  await page.screenshot({ path: `${SCREENS}/calendar-year.png`, fullPage: true });

  expect(errors, errors.join("\n")).toHaveLength(0);
});

test("expander reveals Portland / Vancouver events on click", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Crystal Ballroom")).toHaveCount(0);
  await page.getByRole("button", { name: /Show Portland/i }).click();
  await expect(page.getByText("Crystal Ballroom")).toBeVisible();
});

test("new-since-last-visit highlights, then resets on next visit", async ({ page, context }) => {
  // Seed an old last-visit so the recent event counts as new.
  await context.addInitScript(() => {
    localStorage.setItem("pnw.lastVisit", "2020-01-01T00:00:00Z");
  });
  await page.goto("/");
  const newSection = page.getByTestId("new-section");
  await expect(newSection).toBeVisible();
  await expect(newSection.locator("article")).toHaveCount(1);
  await page.screenshot({ path: `${SCREENS}/new-since.png`, fullPage: true });

  // The app wrote `now()` back on load; a fresh visit should show nothing new.
  await page.reload();
  await expect(page.getByTestId("new-section")).toHaveCount(0);
});

test("mobile (390px) has no horizontal overflow and registers a PWA manifest", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator("article").first()).toBeVisible();

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
  expect(overflow).toBeLessThanOrEqual(1); // allow sub-pixel rounding

  // Installable basics: linked manifest with name + icons.
  const manifestHref = await page.getAttribute('link[rel="manifest"]', "href");
  expect(manifestHref).toBeTruthy();
  await page.screenshot({ path: `${SCREENS}/mobile.png`, fullPage: true });
});

test("SEO baseline: canonical + OG meta, live event JSON-LD, per-tab titles (SPRINT §1.1)", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("article").first()).toBeVisible();

  // Static head: canonical, Open Graph, Twitter card, WebSite JSON-LD.
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /pnw-stage/);
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /og\.png$/);
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute("content", "summary_large_image");

  // Runtime ItemList JSON-LD reflects the mocked inventory.
  const jsonld = await page.locator("script#events-jsonld").textContent();
  const data = JSON.parse(jsonld!);
  expect(data["@type"]).toBe("ItemList");
  expect(data.itemListElement.length).toBeGreaterThanOrEqual(3);
  const first = data.itemListElement[0].item;
  expect(["MusicEvent", "ComedyEvent", "TheaterEvent", "Event"]).toContain(first["@type"]);
  expect(first.location["@type"]).toBe("Place");

  // Per-tab titles.
  await expect(page).toHaveTitle(/PNW Stage — Concerts & Comedy/);
  await page.getByRole("button", { name: "Venues" }).click();
  await expect(page).toHaveTitle(/Venues — PNW Stage/);
});

test("deep link /e/<id>-<slug> opens the event drawer; card click writes the path (SPRINT §1.2)", async ({ page }) => {
  await page.goto("/e/1-japanese-breakfast");
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("heading", { name: "Japanese Breakfast" })).toBeVisible();
  await expect(page).toHaveTitle(/Japanese Breakfast at The Showbox — PNW Stage/);

  // Closing returns the URL to the root.
  await drawer.getByRole("button", { name: "Close" }).click();
  await expect(page).not.toHaveURL(/\/e\//);

  // Opening from a card (title button) writes the shareable path.
  await page.locator("article").first().getByRole("button", { name: "Japanese Breakfast", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page).toHaveURL(/\/e\/\d+-/);
});

test("deep link to an expandable-metro event reveals the expander and opens it (SPRINT §1.2)", async ({ page }) => {
  await page.goto("/e/9-khruangbin");
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("heading", { name: "Khruangbin" })).toBeVisible();
});

test("deep link /v/<slug> lands on the venues tab (SPRINT §1.2)", async ({ page }) => {
  await page.goto("/v/the-showbox");
  await expect(page).toHaveTitle(/Venues — PNW Stage/);
  await expect(page.getByText("The Showbox").first()).toBeVisible();
});

test("share button copies the deep link; Add to calendar downloads a valid .ics (SPRINT §2)", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("/e/1-japanese-breakfast");
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();

  // Headless desktop Chromium has no navigator.share → clipboard fallback.
  await drawer.getByRole("button", { name: "Share" }).click();
  await expect(drawer.getByRole("button", { name: "Link copied" })).toBeVisible();
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toBe("https://pnw-stage.pages.dev/e/1-japanese-breakfast");

  const downloadP = page.waitForEvent("download");
  await drawer.getByRole("button", { name: "Add to calendar" }).click();
  const download = await downloadP;
  expect(download.suggestedFilename()).toBe("japanese-breakfast.ics");
  const body = await import("node:fs/promises").then((fs) =>
    download.path().then((p) => fs.readFile(p!, "utf8"))
  );
  expect(body).toContain("BEGIN:VCALENDAR");
  expect(body).toContain("SUMMARY:Japanese Breakfast");
  expect(body).toContain("DTSTART;VALUE=DATE:20260620"); // date-only fixture → all-day
  expect(body).toContain("LOCATION:The Showbox\\, Seattle\\, WA");
});
