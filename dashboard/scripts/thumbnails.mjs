// `npm run thumbnails`: screenshot what each Docs card opens, for the card's
// preview image (src/features/docs/thumbnails/<slug>.jpg). Re-run after adding
// or changing a document, then `npm run build:backend`.
//
// Starts its own Vite dev server, so nothing else needs to be running. The
// Docs pages make no API calls, so any key gets past the sign-in screen.
import { mkdir, readdir, rm } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";
import { createServer } from "vite";

const OUT = fileURLToPath(new URL("../src/features/docs/thumbnails/", import.meta.url));
const PORT = 5198;
const BASE = `http://localhost:${PORT}`;
// 16:10 like the card's preview area, shrunk to half size for the image.
const VIEWPORT = { width: 1280, height: 800 };

const server = await createServer({ server: { port: PORT, strictPort: true }, logLevel: "error" });
await server.listen();
const browser = await chromium.launch();

try {
  const page = await browser.newPage({ viewport: VIEWPORT, deviceScaleFactor: 0.5 });
  await page.addInitScript(() => sessionStorage.setItem("registration.apiKey", "thumbnails"));

  await page.goto(`${BASE}/docs`, { waitUntil: "networkidle" });
  const cards = await page.$$eval("[data-doc-slug]", (els) =>
    els.map((el) => ({
      slug: el.dataset.docSlug,
      kind: el.dataset.docKind,
      href: el.getAttribute("href"),
    })),
  );

  await mkdir(OUT, { recursive: true });
  // Start clean, so a removed document leaves no stale image behind.
  for (const file of await readdir(OUT)) await rm(join(OUT, file));

  for (const { slug, kind, href } of cards) {
    if (kind === "spreadsheet") continue; // a download, nothing to show
    const path = `${OUT}${slug}.jpg`;
    await page.goto(new URL(href, BASE).href, { waitUntil: "networkidle" });

    if (kind === "diagram") {
      // The image alone, not the dashboard around it.
      await page.locator("main img").screenshot({ path, type: "jpeg", quality: 80 });
    } else if (kind === "page") {
      await page.screenshot({ path, type: "jpeg", quality: 80 });
    } else {
      // A dashboard page: the content under the nav, cropped to 16:10.
      const box = await page.locator("main").boundingBox();
      const clip = { x: box.x, y: box.y, width: box.width, height: (box.width * 10) / 16 };
      await page.screenshot({ path, clip, type: "jpeg", quality: 80 });
    }
    console.log(`${slug}.jpg`);
  }
} finally {
  await browser.close();
  await server.close();
}
