// Checks that the on-phone engine (lib/offline.ts) gives the same answer as the server for the same taps.
// Needs the backend on :8000 with fresh demo data (make demo-reset).  Run: node scripts/offline-parity.mjs
import { build } from "esbuild";
import { pathToFileURL } from "node:url";
import { tmpdir } from "node:os";
import { join } from "node:path";

const API = process.env.API ?? "http://localhost:8000/api/v1";
const out = join(tmpdir(), "vitalis-offline-engine.mjs");
await build({ entryPoints: ["lib/offline.ts"], bundle: true, format: "esm", platform: "node", outfile: out,
  alias: { "@": "." }, logLevel: "error" });
const eng = await import(pathToFileURL(out).href);

const j = async (path, opts = {}) => {
  const r = await fetch(API + path, { ...opts, headers: { "content-type": "application/json", ...(opts.headers ?? {}) } });
  return (await r.json()).data;
};
const bundle = await j("/offline/bundle");
const LOC = { kind: "location", lat: 7.1475, lng: 3.3619 };
const scenarios = {
  "pregnancy bleeding": [LOC, { kind: "emergency", code: "pregnancy" }, { kind: "region", region: "pelvis" },
    { kind: "symptom", code: "BLEEDING_VAGINAL_HEAVY", region: "pelvis" }],
  "can't breathe": [LOC, { kind: "emergency", code: "cant_breathe" }],
  "child very sick": [LOC, { kind: "emergency", code: "child_sick" }],
  "accident": [LOC, { kind: "emergency", code: "accident" }],
  "chest pain": [LOC, { kind: "emergency", code: "chest_pain" }],
  "pregnant, labour pains": [LOC, { kind: "context", age_group: "adult", sex: "female", pregnant: true },
    { kind: "region", region: "lower_abdomen" }, { kind: "symptom", code: "LABOUR_PAINS", region: "lower_abdomen" },
    { kind: "severity", value: 3 }, { kind: "onset", value: "today" }],
  "child with fever": [LOC, { kind: "context", age_group: "under5", sex: "male" }, { kind: "region", region: "whole_body" },
    { kind: "symptom", code: "FEVER", region: "whole_body" }, { kind: "severity", value: 2 }, { kind: "onset", value: "today" }],
};

let failures = 0;
for (const [name, taps] of Object.entries(scenarios)) {
  const keys = await j("/patients/start", { method: "POST", body: "{}" });
  const server = await j("/triage", { method: "POST", body: JSON.stringify({ taps }), headers: { "x-patient-key": keys.device_key } });
  const r = eng.emptyReport();
  for (const t of taps) eng.applyTap(r, t, bundle);
  const phone = eng.evaluateOffline(r, bundle);
  const pick = (x) => ({
    red_flag: x.red_flag.fired, message: x.red_flag.message, care_type: x.care_type, action: x.action_level,
    top: x.hospitals.top.slice(0, 3).map((h) => h.name), excluded: x.hospitals.excluded.map((e) => e.name).sort(),
  });
  const a = pick(server), b = pick(phone);
  // Without signal there is no disease model, so a non-urgent care type may legitimately differ.
  const keysToCompare = server.red_flag.fired || server.care_type === phone.care_type
    ? Object.keys(a) : ["red_flag", "message"];
  const diff = keysToCompare.filter((k) => JSON.stringify(a[k]) !== JSON.stringify(b[k]));
  console.log(`${diff.length ? "DIFF" : "same"}  ${name}${diff.length ? "  " + diff.map((k) => `${k}: server=${JSON.stringify(a[k])} phone=${JSON.stringify(b[k])}`).join(" | ") : ""}`);
  if (diff.length) failures++;
}
process.exit(failures ? 1 : 0);
