// VITALIS public presentation. Run: node build.js  ->  ../VITALIS-presentation.pptx
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const OUT = path.join(__dirname, "..", "VITALIS-presentation.pptx");
const IMG = (n) => path.join(__dirname, "img", n);
const THEME = {
  name: "VITALIS",
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  colors: {
    dk1: "14201C", lt1: "FFFFFF", dk2: "0F5C4A", lt2: "EEF6F3",
    accent1: "0F5C4A", accent2: "134E5E", accent3: "B42318", accent4: "4B5A55", accent5: "F6F8F7", accent6: "7DBBA6",
    hlink: "134E5E", folHlink: "4B5A55",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "VITALIS";
pres.author = "VITALIS team";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "VITALIS Dark",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.3, w: 7.6, h: 1.4, fontSize: 54, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.8, w: 7.6, h: 1.0, fontSize: 24, color: C.background2, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "VITALIS Content",
  background: { color: C.accent5 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.95, fontSize: 32, bold: true, color: C.text1, valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "VITALIS · ITDC 2026", options: { x: 0.6, y: 7.0, w: 4, h: 0.3, fontSize: 10, color: C.accent4, margin: 0 } } },
  ],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent4, align: "right" },
});

// ---------- helpers ----------
const PHONE_RATIO = 780 / 1688;
function phone(slide, img, x, y, h, name) {
  const w = h * PHONE_RATIO;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: x - 0.09, y: y - 0.09, w: w + 0.18, h: h + 0.18, rectRadius: 0.32, fill: { color: C.text1 },
    line: { type: "none" }, shadow: { type: "outer", color: "14201C", opacity: 0.22, blur: 10, offset: 4, angle: 90 },
    objectName: `${name} bezel`,
  });
  slide.addImage({ path: IMG(img), x, y, w, h, objectName: name, altText: name });
  return w;
}
function card(slide, img, x, y, w, ratio, name) {
  const h = w * ratio;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: x - 0.1, y: y - 0.1, w: w + 0.2, h: h + 0.2, rectRadius: 0.12, fill: { color: C.background1 },
    line: { color: "DDE4E1", width: 0.75 }, shadow: { type: "outer", color: "14201C", opacity: 0.12, blur: 12, offset: 4, angle: 90 },
    objectName: `${name} card`,
  });
  slide.addImage({ path: IMG(img), x, y, w, h, objectName: name, altText: name });
  return h;
}
function dot(slide, x, y, label, fill = C.accent1) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: 0.5, h: 0.5, fill: { color: fill }, line: { type: "none" }, objectName: `badge ${label}` });
  slide.addText(label, { x, y, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
}
function point(slide, x, y, w, head, body, n) {
  dot(slide, x, y, n);
  slide.addText([
    { text: head, options: { bold: true, fontSize: 18, color: C.text1, breakLine: true } },
    { text: body, options: { fontSize: 14, color: C.accent4 } },
  ], { x: x + 0.7, y: y - 0.05, w: w - 0.7, h: 1.0, valign: "top", margin: 0, paraSpaceAfter: 2, isTextBox: true });
}
const content = (section) => pres.addSlide({ masterName: "VITALIS Content", sectionTitle: section });
const dark = (section) => pres.addSlide({ masterName: "VITALIS Dark", sectionTitle: section });

// ---------- 1. title ----------
pres.addSection({ title: "Opening" });
let s = dark("Opening");
s.addImage({ path: IMG("icon.png"), x: 0.8, y: 1.1, w: 1.0, h: 1.0, objectName: "VITALIS icon", altText: "VITALIS icon" });
s.addText("VITALIS", { placeholder: "title" });
s.addText("Get the right hospital, fast", { placeholder: "body" });
s.addText("Healthcare coordination for Nigeria · ITDC 2026 · vitalis.olamide.cloud", { x: 0.8, y: 5.2, w: 7.6, h: 0.4, fontSize: 14, color: C.accent6, margin: 0, isTextBox: true });
phone(s, "home.png", 9.6, 0.75, 6.0, "Patient home screen");
s.addNotes("Good afternoon. We are VITALIS. In one sentence: VITALIS takes a family from 'something is wrong' to 'a hospital is ready for you', fast. Everything you'll see is running live at vitalis.olamide.cloud, on synthetic demo data.");

// ---------- 2. problem ----------
pres.addSection({ title: "Problem" });
s = content("Problem");
s.addText("2:07 AM. Which hospital can actually help?", { placeholder: "title" });
const rows = [["Ibara Family Clinic", "Closest, but no obstetrician on duty"], ["Lafenwa General Hospital", "Obstetrician on duty: unknown"], ["Ogun Teaching Hospital", "Availability last updated 12 hours ago"]];
rows.forEach(([n, why], i) => {
  s.addText([
    { text: n, options: { fontSize: 24, bold: true, color: C.text1, strike: "sngStrike", breakLine: true } },
    { text: why, options: { fontSize: 15, color: C.accent4 } },
  ], { x: 0.6, y: 1.75 + i * 1.25, w: 6.4, h: 1.0, margin: 0, valign: "top", isTextBox: true, objectName: `struck hospital ${i + 1}` });
});
s.addText("Demo hospitals. The real gap: in the moment, nobody can see which hospital is able and ready.", { x: 0.6, y: 5.6, w: 6.4, h: 0.7, fontSize: 13, italic: true, color: C.accent4, margin: 0, isTextBox: true });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.6, y: 1.65, w: 5.1, h: 4.75, rectRadius: 0.15, fill: { color: C.background2 }, line: { type: "none" }, objectName: "pain panel" });
point(s, 7.95, 2.0, 4.6, "Families call around", "Minutes lost finding a hospital that can treat this case, tonight.", "1");
point(s, 7.95, 3.4, 4.6, "Chemists refer blind", "The first stop for most people has no view of who is ready.", "2");
point(s, 7.95, 4.8, 4.6, "Records stay behind", "Each hospital keeps its own; allergies don't travel with the patient.", "3");
s.addNotes("Picture this: two in the morning, 34 weeks pregnant, bleeding. The family's first question is the hardest: where do we go? The closest clinic has no obstetrician. Another, nobody knows. A third is big, but its information is twelve hours old. Today families call around, chemists refer without knowing who is ready, and a patient's history stays locked inside each hospital.");

// ---------- 3. solution ----------
pres.addSection({ title: "Solution" });
s = content("Solution");
s.addText("One app, from the first tap to the hospital bed", { placeholder: "title" });
point(s, 0.6, 1.9, 7.4, "Triage in three taps", "What is happening, where, what she sees. No account, no typing. Danger signs jump straight to an emergency plan.", "1");
point(s, 0.6, 3.35, 7.4, "Matched, live referrals", "Only hospitals that can treat the case, ranked by distance and how fresh their availability is. The hospital accepts on its screen.", "2");
point(s, 0.6, 4.8, 7.4, "One record, her consent", "A VITALIS ID per person. History from other hospitals opens only when she allows it.", "3");
phone(s, "emergency.png", 9.4, 1.55, 5.2, "Emergency plan screen");
s.addNotes("VITALIS does three things. Triage in three taps, so anyone can use it in a panic. Matching and live referral, so the family is only offered hospitals that can actually treat them, and the hospital knows they're coming. And one shared record that travels with the patient, opened only with her consent.");

// ---------- 4. family demo ----------
pres.addSection({ title: "Demo" });
s = content("Demo");
s.addText("The family: three taps to an emergency plan", { placeholder: "title" });
[["home.png", "1  What is happening?"], ["body.png", "2  Where is the problem?"], ["symptoms.png", "3  What do you see?"], ["emergency.png", "Emergency plan, best hospitals"]].forEach(([img, cap], i) => {
  const x = 0.85 + i * 3.1;
  phone(s, img, x, 1.6, 4.6, cap);
  s.addText(cap, { x: x - 0.2, y: 6.35, w: 2.5, h: 0.4, fontSize: 14, bold: true, color: C.text1, align: "center", margin: 0, isTextBox: true });
});
s.addNotes("Here is the real app. She taps Pregnancy problem. The browser asks for her location, only to find hospitals near her. She taps where, then what she sees: heavy bleeding. That's a red flag, so the questions stop and she gets an emergency plan with a Call 112 button and the hospitals that can actually help. The bar at the bottom updated live with every tap. A woman's body shows breasts and the chest is labelled 'Chest and breasts'; a pregnant woman is never offered 'swollen belly'.");

// ---------- 5. hospital ----------
s = content("Demo");
s.addText("The hospital says yes before she arrives", { placeholder: "title" });
card(s, "incoming.png", 0.7, 1.75, 6.6, 576 / 1094, "Incoming referral with Accept");
s.addText([
  { text: "Incoming, live: ", options: { bold: true } }, { text: "danger signs, symptoms and ETA arrive on the hospital's screen", options: { breakLine: true } },
  { text: "One tap to accept: ", options: { bold: true } }, { text: "her phone says go now, with directions and what to bring", options: { breakLine: true } },
  { text: "Declined? ", options: { bold: true } }, { text: "VITALIS moves her to the next hospital automatically", options: { breakLine: true } },
  { text: "Alerts and SMS: ", options: { bold: true } }, { text: "reach her even when the app is closed" },
], { x: 0.7, y: 5.4, w: 8.0, h: 1.3, fontSize: 14, color: C.text1, margin: 0, paraSpaceAfter: 4, valign: "top", isTextBox: true });
phone(s, "accepted.png", 9.4, 1.55, 5.2, "Go now screen");
s.addNotes("On the hospital side, the referral appears live on the Incoming screen with the danger signs and ETA. The doctor taps Accept, and within about three seconds her phone says: go now, they're ready for you. If the hospital declines, it must give a reason and VITALIS automatically offers the next best hospital. A push alert and an SMS reach her even if the app is closed.");

// ---------- 6. doctor & AI ----------
s = content("Demo");
s.addText("AI that remembers what another hospital wrote", { placeholder: "title" });
card(s, "safety.png", 0.7, 1.75, 7.6, 576 / 1958, "AI red flag and safety alert");
card(s, "prescribe.png", 3.9, 4.35, 4.4, 648 / 1504, "Prescription blocked");
s.addText([
  { text: "Red flags first, then possible conditions with the evidence for each", options: { bullet: true, breakLine: true } },
  { text: "Our team's diabetes and heart risk models, shown as bands, not diagnoses", options: { bullet: true, breakLine: true } },
  { text: "Medication safety across hospitals: a clash is blocked; overriding needs a reason, and is audited", options: { bullet: true, breakLine: true } },
  { text: "No doses, no prescriptions from the AI", options: { bullet: true } },
], { x: 8.9, y: 1.75, w: 3.85, h: 3.8, fontSize: 15, color: C.text1, margin: 0, paraSpaceAfter: 10, valign: "top", isTextBox: true });
s.addText("AI suggests. The doctor decides.", { x: 8.9, y: 5.75, w: 3.85, h: 0.6, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addNotes("At the bedside, VITALIS AI reads today's visit with her history across hospitals. It raises the red flag, ranks possible conditions with the evidence behind each, runs our team's diabetes and heart models, and here it catches something no single hospital could: an allergy recorded at Ogun Teaching Hospital, so the usual blood-pressure medicine is blocked. The doctor can override, but must give a reason, and it's audited. The AI never gives doses. It suggests; the doctor decides.");

// ---------- 7. every role ----------
s = content("Demo");
s.addText("Every role, one journey", { placeholder: "title" });
const roles = [
  ["Family", "Triage, referral status, her record"], ["Chemist", "Walk-in triage, vitals, live referrals"],
  ["Reception", "Incoming, arrival, name and NHIA number"], ["Nurse", "Vitals beside the chemist's readings"],
  ["Doctor", "Record, AI, safe prescribing, orders"], ["Lab", "Sample collected, result, verify"],
  ["Radiology", "Its own worklist, report, verify"], ["Admins", "Verify hospitals, staff and chemists; audit"],
];
roles.forEach(([r, d], i) => {
  const x = 0.6 + (i % 4) * 3.1, y = 1.7 + Math.floor(i / 4) * 1.55;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.9, h: 1.35, rectRadius: 0.12, fill: { color: C.background1 }, line: { color: "DDE4E1", width: 0.75 }, objectName: `role ${r}` });
  dot(s, x + 0.2, y + 0.2, r[0], i % 2 ? C.accent2 : C.accent1);
  s.addText([{ text: r, options: { bold: true, fontSize: 17, color: C.text1, breakLine: true } }, { text: d, options: { fontSize: 13, color: C.accent4 } }],
    { x: x + 0.85, y: y + 0.15, w: 1.95, h: 1.1, margin: 0, valign: "top", isTextBox: true });
});
card(s, "lab.png", 0.7, 5.05, 7.0, 540 / 2217, "Lab worklist");
s.addText("Each department sees only its own orders. Only verified results go back to the doctor.", { x: 8.1, y: 5.1, w: 4.6, h: 1.2, fontSize: 15, color: C.text1, margin: 0, valign: "top", isTextBox: true });
s.addNotes("VITALIS covers the whole journey: the family, the chemist on the corner, and every hospital role, from reception to radiology, plus the admins who verify every hospital and chemist before they appear to patients. Lab and radiology each get their own worklist; lab samples are marked as collected, and only verified results go back to the doctor.");

// ---------- 8. consent ----------
pres.addSection({ title: "Trust" });
s = content("Trust");
s.addText("Her record opens only when she says yes", { placeholder: "title" });
phone(s, "request.png", 0.9, 1.55, 5.2, "Hospital asks to see her record");
phone(s, "wholooked.png", 3.75, 1.55, 5.2, "Who looked");
point(s, 7.0, 1.8, 5.7, "Allow or Don't allow", "A hospital asks; she decides on her phone. Access lasts 24 hours.", "1");
point(s, 7.0, 3.0, 5.7, "Or a QR code", "Works once, expires in 10 minutes.", "2");
point(s, 7.0, 4.2, 5.7, "Who looked", "Every view is logged and shown to her. She can stop access any time.", "3");
point(s, 7.0, 5.4, 5.7, "Safety first", "Allergies are always visible to the treating hospital.", "4");
s.addNotes("Trust is the foundation. A hospital sees its own visits; everything from other hospitals opens only when she allows it, with a tap or a one-time QR code that expires in ten minutes. She sees every hospital that looked and can stop access at any time. Allergies are the one exception, always visible, because they keep her safe.");

// ---------- 9. NHIA ----------
s = content("Trust");
s.addText("Built to work alongside the NHIA", { placeholder: "title" });
const col = (x, head, sub, lines, fill, name) => {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.65, w: 5.9, h: 2.7, rectRadius: 0.15, fill: { color: fill }, line: { type: "none" }, objectName: name });
  s.addText([{ text: head, options: { bold: true, fontSize: 22, color: C.background1, breakLine: true } }, { text: sub, options: { fontSize: 13, color: C.background2, breakLine: true } },
    ...lines.map((l, i) => ({ text: l, options: { fontSize: 15, color: C.background1, bullet: true, breakLine: i < lines.length - 1 } }))],
    { x: x + 0.35, y: 1.85, w: 5.2, h: 2.4, margin: 0, valign: "top", paraSpaceAfter: 6, isTextBox: true });
};
col(0.6, "NHIA", "National Health Insurance Authority, formerly the NHIS", ["Helps Nigerians pay for care", "Mandatory health insurance since the NHIA Act 2022", "A Vulnerable Group Fund for those who can't pay"], C.accent2, "NHIA panel");
col(6.83, "VITALIS", "Healthcare coordination", ["Helps them reach the right care, fast", "Live referrals to hospitals that can treat", "One record, opened with her consent"], C.accent1, "VITALIS panel");
card(s, "details.png", 0.7, 4.85, 6.4, 236 / 1504, "Patient details with NHIA number");
s.addText("Today: her NHIA number travels with her VITALIS ID, so reception sees it on arrival. Next: show which suggested hospitals are NHIA-accredited.", { x: 7.5, y: 4.75, w: 5.2, h: 1.4, fontSize: 15, color: C.text1, margin: 0, valign: "top", isTextBox: true });
s.addNotes("VITALIS is built to work alongside the NHIA, formerly the NHIS. The NHIA helps Nigerians pay for care; VITALIS helps them reach the right care, fast. Insurance makes care affordable; coordination makes it reachable. Today a patient's NHIA number travels with her VITALIS ID, so reception sees it the moment she arrives. Next, we want suggested hospitals to show NHIA accreditation, so an insured patient goes where her cover works.");

// ---------- 10. under the hood ----------
pres.addSection({ title: "Build" });
s = content("Build");
s.addText("Running today, not a mock-up", { placeholder: "title" });
const flow = [["Phone app (PWA)", "Installs, works offline, light and dark"], ["Secure API", "Roles, facility scoping, audit log"], ["Engines", "Red flags · matching · AI + ML models"], ["Live updates", "Server events · web push · SMS"]];
flow.forEach(([h, d], i) => {
  const x = 0.6 + i * 3.15;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.75, w: 2.8, h: 1.6, rectRadius: 0.12, fill: { color: C.background1 }, line: { color: "DDE4E1", width: 0.75 }, objectName: `stage ${h}` });
  s.addText([{ text: h, options: { bold: true, fontSize: 17, color: C.accent1, breakLine: true } }, { text: d, options: { fontSize: 13, color: C.accent4 } }], { x: x + 0.25, y: 1.95, w: 2.35, h: 1.25, margin: 0, valign: "top", isTextBox: true });
  if (i < 3) s.addShape(pres.shapes.CHEVRON, { x: x + 2.89, y: 2.43, w: 0.2, h: 0.3, fill: { color: C.accent6 }, line: { type: "none" }, objectName: `arrow ${i + 1}` });
});
[["107", "automated tests"], ["6", "hospital roles"], ["24/7", "live at vitalis.olamide.cloud"]].forEach(([n, l], i) => {
  const x = 0.6 + i * 4.2;
  s.addText([{ text: n, options: { fontSize: 60, bold: true, color: C.accent1, breakLine: true } }, { text: l, options: { fontSize: 16, color: C.text1 } }], { x, y: 4.1, w: 3.9, h: 1.9, margin: 0, valign: "top", isTextBox: true, objectName: `stat ${l}` });
});
s.addText("Next.js PWA · FastAPI · PostgreSQL · Docker on one VPS · synthetic data only", { x: 0.6, y: 6.25, w: 12, h: 0.4, fontSize: 13, color: C.accent4, margin: 0, isTextBox: true });
s.addNotes("This is not a mock-up. It's a progressive web app that installs on any phone and works offline, a secure API with role and facility scoping and a full audit log, our triage, matching and AI engines, and live updates through server events, web push and SMS. It has 107 automated tests and it's live right now.");

// ---------- 11. next ----------
s = content("Build");
s.addText("What comes next", { placeholder: "title" });
[["Clinical review", "Red-flag rules and medicine safety checked by clinicians"], ["Nigerian languages", "Pidgin, Yoruba, Hausa and Igbo, with voice prompts"], ["NHIA-ready matching", "Accredited facilities shown for insured patients"], ["A pilot in Ogun", "Hospitals and chemists in Abeokuta first"]].forEach(([h, d], i) => {
  const x = 0.6 + i * 3.15;
  dot(s, x, 2.0, String(i + 1));
  if (i < 3) s.addShape(pres.shapes.LINE, { x: x + 0.6, y: 2.25, w: 2.45, h: 0, line: { color: "7DBBA6", width: 2 }, objectName: `step line ${i + 1}` });
  s.addText([{ text: h, options: { bold: true, fontSize: 18, color: C.text1, breakLine: true } }, { text: d, options: { fontSize: 14, color: C.accent4 } }], { x, y: 2.75, w: 2.85, h: 1.6, margin: 0, valign: "top", isTextBox: true });
});
s.addText("Start where people already go first: the chemist on the corner.", { x: 0.6, y: 5.2, w: 9.4, h: 0.8, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addNotes("Next: a clinical review of our rules, the four major Nigerian languages with voice prompts, NHIA-ready matching, and a pilot in Abeokuta, starting with the chemists where people already go first.");

// ---------- 12. close ----------
pres.addSection({ title: "Close" });
s = dark("Close");
s.addText([{ text: "From “something is wrong”", options: { breakLine: true } }, { text: "to “a hospital is ready for you”", options: { color: C.accent6 } }],
  { x: 0.8, y: 2.4, w: 8.2, h: 2.0, fontSize: 36, bold: true, color: C.background1, margin: 0, valign: "top", isTextBox: true, objectName: "closing line" });
s.addText("Try it now: vitalis.olamide.cloud", { x: 0.8, y: 4.7, w: 8.2, h: 0.6, fontSize: 24, color: C.background2, margin: 0, isTextBox: true });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.4, y: 1.9, w: 3.2, h: 3.2, rectRadius: 0.2, fill: { color: C.background1 }, line: { type: "none" }, objectName: "QR panel" });
s.addImage({ path: IMG("qr.png"), x: 9.6, y: 2.1, w: 2.8, h: 2.8, objectName: "QR code to vitalis.olamide.cloud", altText: "QR code linking to vitalis.olamide.cloud" });
s.addText("Scan to open VITALIS", { x: 9.4, y: 5.25, w: 3.2, h: 0.4, fontSize: 14, color: C.background2, align: "center", margin: 0, isTextBox: true });
s.addImage({ path: IMG("icon.png"), x: 0.8, y: 1.1, w: 0.9, h: 0.9, objectName: "VITALIS icon", altText: "VITALIS icon" });
s.addNotes("VITALIS: from 'something is wrong' to 'a hospital is ready for you'. Scan the code and try it now. Thank you.");

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
