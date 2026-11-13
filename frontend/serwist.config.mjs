// @ts-check
// Builds the service worker after `next build` (works with Turbopack): `serwist build`.
import { serwist } from "@serwist/next/config";

export default serwist({
  swSrc: "app/sw.ts",
  swDest: "public/sw.js",
  // Dev-only pages 404 in production; one failed precache entry stops the whole worker installing.
  manifestTransforms: [
    async (entries) => ({ manifest: entries.filter((e) => !/(^|\/)dev\//.test(e.url)), warnings: [] }),
  ],
});
