// Event sharing via the Web Share API with a clipboard fallback (SPRINT §2).
import { SITE_URL } from "./seo";
import { eventPath } from "./routes";
import { showDate } from "./format";
import type { EventRow } from "./types";

export type ShareResult = "shared" | "copied" | "dismissed";

export function shareUrlFor(e: EventRow): string {
  return `${SITE_URL}${eventPath(e)}`;
}

export async function shareEvent(e: EventRow): Promise<ShareResult> {
  const url = shareUrlFor(e);
  const title = `${e.headliner ?? e.title} at ${e.venue_name}`;
  if (typeof navigator.share === "function") {
    try {
      await navigator.share({ title, text: `${title} — ${showDate(e)}`, url });
      return "shared";
    } catch {
      // User cancelled the sheet (or the payload was rejected) — don't
      // surprise them by writing to the clipboard instead.
      return "dismissed";
    }
  }
  await navigator.clipboard.writeText(url);
  return "copied";
}
