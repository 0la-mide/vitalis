// @ts-check
// Builds the service worker after `next build` (works with Turbopack): `serwist build`.
import { serwist } from "@serwist/next/config";

export default serwist({
  swSrc: "app/sw.ts",
  swDest: "public/sw.js",
});
