// VITALIS presentation. Run: node build.js  ->  ../VITALIS-presentation.pptx
// One idea per slide. Light slides explain, dark slides land the point. Every number on a slide is true of the build.
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
    dk1: "1D1D1F", lt1: "FFFFFF", dk2: "0B1110", lt2: "F5F5F7",
    accent1: "0F6E55", accent2: "134E5E", accent3: "B42318", accent4: "6E6E73", accent5: "E8F3EF", accent6: "6FD6AE",
    hlink: "134E5E", folHlink: "6E6E73",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "VITALIS";
pres.author = "VITALIS team";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const LINE = "E3E3E8";

pres.defineSlideMaster({ title: "VITALIS Dark", background: { color: C.text2 }, objects: [] });
pres.defineSlideMaster({
  title: "VITALIS Light",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 0.78, w: 11.9, h: 0.85, fontSize: 34, bold: true, color: C.text1, valign: "top", align: "left", margin: 0 }, text: "" } },
    { text: { text: "VITALIS", options: { x: 0.7, y: 7.0, w: 3, h: 0.3, fontSize: 10, bold: true, color: C.accent4, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent4, align: "right" },
});

// ---------- helpers ----------
const PHONE = 780 / 1688;
const T = (slide, text, o) => slide.addText(text, { margin: 0, valign: "top", isTextBox: true, ...o });
const light = (section, eyebrow, title) => {
  const s = pres.addSlide({ masterName: "VITALIS Light", sectionTitle: section });
  T(s, eyebrow.toUpperCase(), { x: 0.7, y: 0.42, w: 8, h: 0.3, fontSize: 12, bold: true, color: C.accent1, charSpacing: 2 });
  s.addText(title, { placeholder: "title" });
  return s;
};
const dark = (section) => pres.addSlide({ masterName: "VITALIS Dark", sectionTitle: section });

function phone(slide, img, x, y, h, name) {
  const w = h * PHONE;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: x - 0.08, y: y - 0.08, w: w + 0.16, h: h + 0.16, rectRadius: 0.3, fill: { color: "1D1D1F" },
    line: { type: "none" }, shadow: { type: "outer", color: "000000", opacity: 0.2, blur: 14, offset: 5, angle: 90 },
    objectName: `${name} bezel`,
  });
  slide.addImage({ path: IMG(img), x, y, w, h, objectName: name, altText: name });
  return w;
}
function card(slide, img, x, y, w, ratio, name) {
  const h = w * ratio;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: x - 0.08, y: y - 0.08, w: w + 0.16, h: h + 0.16, rectRadius: 0.1, fill: { color: C.background1 },
    line: { color: LINE, width: 0.75 }, shadow: { type: "outer", color: "000000", opacity: 0.1, blur: 14, offset: 4, angle: 90 },
    objectName: `${name} card`,
  });
  slide.addImage({ path: IMG(img), x, y, w, h, objectName: name, altText: name });
  return h;
}
function num(slide, x, y, label, fill = C.accent1, d = 0.46) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" }, objectName: `marker ${label}` });
  T(slide, label, { x, y, w: d, h: d, fontSize: 15, bold: true, color: C.background1, align: "center", valign: "middle" });
}
function point(slide, x, y, w, head, body, n, h = 1.0) {
  if (n) num(slide, x, y, n);
  const dx = n ? 0.68 : 0;
  T(slide, [
    { text: head, options: { bold: true, fontSize: 18, color: C.text1, breakLine: true } },
    { text: body, options: { fontSize: 14, color: C.accent4 } },
  ], { x: x + dx, y: y - 0.02, w: w - dx, h, paraSpaceAfter: 3 });
}
const box = (slide, x, y, w, h, fill, name, line) => slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x, y, w, h, rectRadius: 0.14, fill: { color: fill }, line: line ? { color: line, width: 0.75 } : { type: "none" }, objectName: name,
});
const chevron = (slide, x, y, name, color = C.accent6, w = 0.22, h = 0.34) =>
  slide.addShape(pres.shapes.CHEVRON, { x, y, w, h, fill: { color }, line: { type: "none" }, objectName: name });

// =====================================================================================================
// OPENING
// =====================================================================================================
pres.addSection({ title: "Opening" });
let s = dark("Opening");
s.addImage({ path: IMG("icon.png"), x: 0.9, y: 1.3, w: 0.95, h: 0.95, objectName: "VITALIS icon", altText: "VITALIS icon" });
T(s, "VITALIS", { x: 0.9, y: 2.55, w: 7.8, h: 1.2, fontSize: 66, bold: true, color: C.background1 });
T(s, "Get the right hospital, fast.", { x: 0.9, y: 3.8, w: 7.8, h: 0.7, fontSize: 30, color: C.accent6 });
T(s, "Healthcare coordination for Nigeria  ·  ITDC 2026  ·  vitalis.olamide.cloud", { x: 0.9, y: 5.7, w: 7.8, h: 0.4, fontSize: 14, color: C.accent4 });
phone(s, "home.png", 9.35, 0.75, 6.0, "Patient home screen");
s.addNotes("Good afternoon. We are VITALIS. In one sentence: VITALIS takes a family from 'something is wrong' to 'a hospital is ready for you', fast. Everything you will see is running live at vitalis.olamide.cloud, on synthetic demo data.");

s = dark("Opening");
T(s, "2:07 AM.", { x: 0.9, y: 1.6, w: 11.5, h: 1.7, fontSize: 96, bold: true, color: C.background1 });
T(s, "34 weeks pregnant. Bleeding.", { x: 0.9, y: 3.55, w: 11.5, h: 0.7, fontSize: 32, color: C.accent4 });
T(s, "Which hospital can actually help her?", { x: 0.9, y: 4.25, w: 11.5, h: 0.7, fontSize: 32, bold: true, color: C.accent6 });
s.addNotes("Two in the morning. Thirty-four weeks pregnant, and bleeding. The family's first question is the hardest one: where do we go? Not the closest hospital. The one that can actually help her, tonight.");

const PROBLEMS = [
  ["Nobody knows who is ready", "Which hospital has an obstetrician, blood or a theatre tonight? Families call around."],
  ["The first stop refers blind", "Most people see a chemist first. He can't see which hospital can help."],
  ["Records stay behind", "Each hospital keeps its own file. Allergies don't travel with the patient."],
  ["Signal and power fail", "Apps that need the internet stop exactly when they are needed."],
  ["Cost decides the door", "Families don't know where their NHIA cover or free maternal care applies."],
];
s = light("Opening", "The problem", "Finding care in Nigeria is guesswork.");
PROBLEMS.forEach(([h, b], i) => {
  const x = 0.7 + i * 2.43, w = 2.23;
  box(s, x, 1.95, w, 3.6, C.background2, `problem ${i + 1}`);
  T(s, `0${i + 1}`, { x: x + 0.25, y: 2.2, w: 1.5, h: 0.8, fontSize: 40, bold: true, color: C.accent3 });
  T(s, [{ text: h, options: { bold: true, fontSize: 17, color: C.text1, breakLine: true } }, { text: b, options: { fontSize: 13, color: C.accent4 } }],
    { x: x + 0.25, y: 3.1, w: w - 0.45, h: 2.3, paraSpaceAfter: 6 });
});
T(s, "Each one costs minutes. In an emergency, minutes are the difference.", { x: 0.7, y: 5.95, w: 11.9, h: 0.5, fontSize: 20, bold: true, color: C.accent1 });
s.addNotes("We started by listing what actually goes wrong. One: nobody can see which hospital is able and ready tonight. Two: most people see a chemist first, and the chemist refers blind. Three: records stay locked inside each hospital, so an allergy recorded in one is unknown in the next. Four: signal and power fail, so apps that need the internet stop exactly when they are needed. Five: cost decides the door, because families don't know where their NHIA cover or free maternal care applies. Each one costs minutes. We built VITALIS to answer all five.");

// =====================================================================================================
// THE APP
// =====================================================================================================
pres.addSection({ title: "The app" });
s = dark("The app");
T(s, "MEET VITALIS", { x: 0.9, y: 1.0, w: 6, h: 0.35, fontSize: 13, bold: true, color: C.accent6, charSpacing: 2 });
T(s, "One app. From the first tap to the hospital bed.", { x: 0.9, y: 1.45, w: 11.5, h: 1.7, fontSize: 44, bold: true, color: C.background1 });
[["Three taps", "No account, no typing. Danger signs jump straight to an emergency plan."],
  ["Matched, live referral", "Only hospitals that can treat her. They accept before she arrives."],
  ["One record, her consent", "A VITALIS ID that carries her history, opened only when she says yes."]].forEach(([h, b], i) => {
  const x = 0.9 + i * 4.0;
  s.addShape(pres.shapes.LINE, { x, y: 3.9, w: 3.5, h: 0, line: { color: C.accent6, width: 2 }, objectName: `pillar rule ${i + 1}` });
  T(s, [{ text: h, options: { bold: true, fontSize: 22, color: C.background1, breakLine: true } }, { text: b, options: { fontSize: 15, color: "A1A1A6" } }],
    { x, y: 4.15, w: 3.5, h: 1.8, paraSpaceAfter: 6 });
});
s.addNotes("This is VITALIS. One app, from the first tap to the hospital bed. It does three things. Triage in three taps, so anyone can use it in a panic. Matching and live referral, so the family is only offered hospitals that can actually treat her, and the hospital accepts before she arrives. And one record that travels with her, opened only with her consent.");

s = light("The app", "The family", "Three taps to an emergency plan.");
[["home.png", "1  What is happening?"], ["body.png", "2  Where is it?"], ["symptoms.png", "3  What do you see?"], ["emergency.png", "The plan and the right hospitals"]].forEach(([img, cap], i) => {
  const x = 0.95 + i * 3.1;
  phone(s, img, x, 1.95, 4.3, cap);
  T(s, cap, { x: x - 0.35, y: 6.4, w: 2.7, h: 0.4, fontSize: 14, bold: true, color: i === 3 ? C.accent1 : C.text1, align: "center" });
});
s.addNotes("Here is the real app. She taps Pregnancy problem. The phone asks for her location, only to find hospitals near her. She taps where, then what she sees: heavy bleeding. That is a danger sign, so the questions stop and she gets an emergency plan, a Call 112 button, and only the hospitals that can actually help. No account. No typing.");

s = light("The app", "The hospital", "The hospital says yes before she arrives.");
card(s, "incoming.png", 0.8, 1.95, 6.3, 576 / 1094, "Incoming referral with Accept");
const STEPS = [["Taps", "Danger signs found"], ["Matched", "Only able hospitals"], ["Accepted", "On the hospital's screen"], ["Arrived", "Reception checks her in"]];
STEPS.forEach(([h, b], i) => {
  const x = 0.8 + i * 1.75;
  if (i < 3) s.addShape(pres.shapes.LINE, { x: x + 0.46, y: 5.73, w: 1.29, h: 0, line: { color: C.accent6, width: 2 }, objectName: `journey line ${i + 1}` });
  num(s, x, 5.5, String(i + 1));
  T(s, [{ text: h, options: { bold: true, fontSize: 15, color: C.text1, breakLine: true } }, { text: b, options: { fontSize: 11, color: C.accent4 } }], { x: x - 0.1, y: 6.05, w: 1.65, h: 0.75 });
});
phone(s, "accepted.png", 9.35, 1.6, 5.2, "Go now screen");
s.addNotes("On the hospital side, the referral appears live, with the danger signs and the ETA. The doctor taps Accept and her phone says: go now, they are ready for you. If the hospital declines, it gives a reason and VITALIS moves her to the next best hospital automatically. Alerts and an SMS reach her even if the app is closed.");

s = light("The app", "The doctor", "AI that remembers what another hospital wrote.");
card(s, "safety.png", 0.8, 1.95, 7.5, 576 / 1958, "AI red flag and safety alert");
card(s, "prescribe.png", 3.9, 4.55, 4.4, 648 / 1504, "Prescription blocked");
T(s, [
  { text: "Danger signs first, then possible conditions with the evidence for each", options: { bullet: true, breakLine: true } },
  { text: "Our own diabetes and heart risk models, shown as bands, not diagnoses", options: { bullet: true, breakLine: true } },
  { text: "A medicine clash with history from another hospital is blocked; overriding needs a reason and is logged", options: { bullet: true, breakLine: true } },
  { text: "No doses, no prescriptions from the AI", options: { bullet: true } },
], { x: 8.9, y: 1.95, w: 3.8, h: 3.9, fontSize: 15, color: C.text1, paraSpaceAfter: 10 });
T(s, "AI suggests. The doctor decides.", { x: 8.9, y: 5.95, w: 3.8, h: 0.5, fontSize: 20, bold: true, color: C.accent1 });
s.addNotes("At the bedside, VITALIS AI reads today's visit together with her history across hospitals. It raises the danger sign, ranks possible conditions with the evidence behind each, and runs our own diabetes and heart models. Here it catches something no single hospital could: an allergy recorded at another hospital, so the usual blood-pressure medicine is blocked. The doctor can override, with a reason, and it is logged. The AI never gives doses. It suggests; the doctor decides.");

// =====================================================================================================
// THE PEOPLE
// =====================================================================================================
pres.addSection({ title: "The people" });
s = light("The people", "Everyone who touches the journey", "Nine roles. One journey.");
box(s, 0.7, 1.95, 3.1, 3.55, C.background2, "community zone");
T(s, "IN THE COMMUNITY", { x: 0.95, y: 2.1, w: 2.6, h: 0.3, fontSize: 11, bold: true, color: C.accent4, charSpacing: 1 });
[["Family", "Triage, referral, her own record"], ["Chemist", "Walk-in triage, vitals, live referral"]].forEach(([h, b], i) => {
  box(s, 0.95, 2.55 + i * 1.4, 2.6, 1.2, C.background1, `${h} card`, LINE);
  T(s, [{ text: h, options: { bold: true, fontSize: 17, color: C.text1, breakLine: true } }, { text: b, options: { fontSize: 12, color: C.accent4 } }], { x: 1.15, y: 2.7 + i * 1.4, w: 2.25, h: 0.95 });
});
s.addShape(pres.shapes.RIGHT_ARROW, { x: 3.88, y: 3.5, w: 0.55, h: 0.45, fill: { color: C.accent1 }, line: { type: "none" }, objectName: "referral arrow" });
T(s, "live\nreferral", { x: 3.8, y: 4.0, w: 0.72, h: 0.5, fontSize: 9, color: C.accent1, align: "center", bold: true });
box(s, 4.5, 1.95, 8.13, 3.55, C.background2, "hospital zone");
T(s, "IN THE HOSPITAL", { x: 4.75, y: 2.1, w: 4, h: 0.3, fontSize: 11, bold: true, color: C.accent4, charSpacing: 1 });
box(s, 4.75, 2.5, 7.63, 0.7, C.accent2, "hospital admin bar");
T(s, [{ text: "Hospital admin  ", options: { bold: true, color: C.background1 } }, { text: "approves staff, keeps availability, cost and coverage up to date", options: { color: "D7E6EA" } }],
  { x: 4.95, y: 2.5, w: 7.3, h: 0.7, fontSize: 14, valign: "middle" });
[["Reception", "Arrival, name, NHIA number"], ["Nurse", "Vitals beside the chemist's"], ["Doctor", "History, AI, safe prescribing"], ["Lab · Radiology", "Own worklists, verified results"]].forEach(([h, b], i) => {
  const x = 4.75 + i * 1.97;
  box(s, x, 3.45, 1.72, 1.8, C.background1, `${h} card`, LINE);
  T(s, [{ text: h, options: { bold: true, fontSize: 15, color: C.text1, breakLine: true } }, { text: b, options: { fontSize: 12, color: C.accent4 } }], { x: x + 0.15, y: 3.6, w: 1.45, h: 1.55, paraSpaceAfter: 4 });
  if (i < 3) chevron(s, x + 1.77, 4.18, `flow ${i + 1}`, C.accent6, 0.17, 0.32);
});
box(s, 0.7, 5.75, 11.93, 0.75, C.text2, "network admin bar");
T(s, [{ text: "Network admin  ", options: { bold: true, color: C.background1 } }, { text: "verifies every hospital and chemist before a patient ever sees them", options: { color: "A1A1A6" } }],
  { x: 0.95, y: 5.75, w: 11.5, h: 0.75, fontSize: 15, valign: "middle" });
s.addNotes("VITALIS is not an app for one person. It covers everyone who touches the journey. In the community: the family, and the chemist on the corner. In the hospital: reception, the nurse, the doctor, the lab and radiology, each with their own screen. The hospital admin approves staff and keeps availability, cost and coverage current. And above it all, the network admin verifies every hospital and every chemist before a patient ever sees them. Nine roles. One journey.");

s = light("The people", "The patient", "Her history, in her hands.");
phone(s, "P_addrecord.png", 0.95, 1.85, 4.9, "Add to my record");
phone(s, "P_record2.png", 3.65, 1.85, 4.9, "Her record with a patient-reported allergy");
point(s, 6.6, 2.0, 6.0, "Allergies, conditions, medicines, family history", "She adds them herself, in plain words, from her phone.", "1");
point(s, 6.6, 3.1, 6.0, "Marked “Reported by you”", "Doctors see what she reported apart from what a hospital confirmed.", "2");
point(s, 6.6, 4.2, 6.0, "It keeps her safe", "An allergy she adds is checked before any prescription, at any hospital.", "3");
point(s, 6.6, 5.3, 6.0, "A phone number is optional. No email.", "Her VITALIS ID is enough. Fewer details to lose or leak.", "4");
s.addNotes("A record should not only be what hospitals wrote. In VITALIS she can add her own allergies, conditions, medicines and family history, in plain words. They are marked 'Reported by you', so a doctor can tell what she said from what a hospital confirmed, and an allergy she adds is checked before any prescription, at any hospital. We ask for a phone number only if she wants alerts by SMS, and we never ask for an email. Her VITALIS ID is enough.");

s = light("The people", "The chemist", "The chemist on the corner becomes the front door.");
phone(s, "worker.png", 0.95, 1.85, 4.9, "Chemist triage");
phone(s, "P_month.png", 3.65, 1.85, 4.9, "The chemist's month");
point(s, 6.6, 2.0, 6.0, "Triage the walk-in", "Same three taps, plus the vitals he takes in the shop.", "1");
point(s, 6.6, 3.1, 6.0, "Refer live to a ready hospital", "The hospital sees his readings and accepts on its screen.", "2");
point(s, 6.6, 4.2, 6.0, "See his month", "Patients referred, emergencies caught, patients who reached hospital.", "3");
point(s, 6.6, 5.3, 6.0, "Verified first", "No chemist refers until the network has checked him.", "4");
s.addNotes("For most Nigerians the first stop is not a hospital, it is the chemist on the corner. VITALIS turns that chemist into the front door. He triages the walk-in with the same three taps plus the vitals he takes in the shop, and refers live to a hospital that is ready. He sees his month: how many he referred, how many emergencies he caught, and how many reached hospital. And no chemist refers anyone until the network has verified him.");

// =====================================================================================================
// ACCESS
// =====================================================================================================
pres.addSection({ title: "Access" });
s = light("Access", "Consent", "Her record opens only when she says yes.");
phone(s, "request.png", 0.95, 1.85, 4.9, "Hospital asks to see her record");
phone(s, "wholooked.png", 3.65, 1.85, 4.9, "Who looked");
point(s, 6.6, 2.0, 6.0, "Allow or Don't allow", "A hospital asks; she decides on her phone. Access lasts 24 hours.", "1");
point(s, 6.6, 3.1, 6.0, "Or a QR code", "Works once and expires in 10 minutes.", "2");
point(s, 6.6, 4.2, 6.0, "Who looked", "Every view is logged and shown to her. She can stop access any time.", "3");
point(s, 6.6, 5.3, 6.0, "Safety first", "Allergies are always visible to the hospital treating her.", "4");
s.addNotes("Trust is the foundation. A hospital sees its own visits. Everything from other hospitals opens only when she allows it: a tap that lasts 24 hours, or a QR code that works once and expires in ten minutes. She sees every hospital that looked, and can stop access at any time. Allergies are the one exception, always visible to the hospital treating her, because they keep her safe.");

s = light("Access", "Permissions", "Everyone sees what their job needs. Nothing more.");
const COLS = ["Accept referrals", "Arrival and identity", "Vitals", "Notes, orders, prescribing", "Lab and imaging results", "Staff, cost and coverage", "Verify hospitals and chemists"];
const ROWS = [
  ["Reception", [0, 1, 0, 0, 0, 0, 0]], ["Nurse", [1, 1, 1, 0, 0, 0, 0]], ["Doctor", [1, 0, 1, 1, 0, 0, 0]],
  ["Lab", [0, 0, 0, 0, 1, 0, 0]], ["Radiology", [0, 0, 0, 0, 1, 0, 0]], ["Hospital admin", [1, 1, 0, 0, 0, 1, 0]], ["Network admin", [0, 0, 0, 0, 0, 0, 1]],
];
const MX = 3.0, CW = 1.38, RY = 2.75, RH = 0.47;
COLS.forEach((c, j) => T(s, c, { x: MX + j * CW, y: 1.9, w: CW - 0.1, h: 0.8, fontSize: 12, bold: true, color: C.text1, align: "center", valign: "bottom" }));
ROWS.forEach(([r, v], i) => {
  const y = RY + i * RH;
  if (i % 2 === 0) s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y, w: MX + COLS.length * CW - 0.7, h: RH, fill: { color: C.background2 }, line: { type: "none" }, objectName: `row band ${r}` });
  T(s, r, { x: 0.85, y, w: 2.1, h: RH, fontSize: 15, bold: true, color: C.text1, valign: "middle" });
  v.forEach((on, j) => {
    if (!on) return;
    const d = 0.22;
    s.addShape(pres.shapes.OVAL, { x: MX + j * CW + (CW - 0.1) / 2 - d / 2, y: y + RH / 2 - d / 2, w: d, h: d, fill: { color: C.accent1 }, line: { type: "none" }, objectName: `${r} can ${COLS[j]}` });
  });
});
T(s, "Hospital staff see only their own hospital's patients. History from other hospitals needs her consent. Every view is logged.", { x: 0.7, y: 6.15, w: 11.9, h: 0.5, fontSize: 15, color: C.accent4 });
s.addNotes("Access is by role, and it is enforced on the server, not just hidden in the app. Reception handles arrival and identity. Nurses take vitals. Only doctors write notes, order tests and prescribe. Lab and radiology see only their own worklists. The hospital admin manages staff, cost and coverage. Only the network admin can verify hospitals and chemists. And every hospital sees only its own patients; anything from another hospital needs her consent, and every view is logged.");

// =====================================================================================================
// AVAILABILITY
// =====================================================================================================
pres.addSection({ title: "Availability" });
s = dark("Availability");
T(s, "AVAILABILITY", { x: 0.9, y: 1.4, w: 6, h: 0.35, fontSize: 13, bold: true, color: C.accent6, charSpacing: 2 });
T(s, "No signal.\nStill works.", { x: 0.9, y: 1.85, w: 7.8, h: 2.6, fontSize: 64, bold: true, color: C.background1 });
T(s, "Power cuts and dead zones are normal in Nigeria. VITALIS was built for them, not around them.", { x: 0.9, y: 4.65, w: 7.2, h: 1.2, fontSize: 22, color: "A1A1A6" });
phone(s, "P_offline.png", 9.35, 0.75, 6.0, "Emergency plan with no signal");
s.addNotes("Now the question every Nigerian will ask: what happens when there is no network? Power cuts and dead zones are normal here, and an emergency app that needs the internet fails exactly when it is needed. So VITALIS was built for no signal, not around it. This is the same emergency plan, with the phone offline.");

s = light("Availability", "How it works offline", "No signal is a delay, not a dead end.");
[["home.png", "Once installed, it saves the ready hospitals near her"], ["P_offline.png", "No signal: triage runs on the phone, same rules as the server"],
  ["P_saved.png", "Her request is saved on the phone"], ["P_sent.png", "Signal returns: sent to the hospital automatically"]].forEach(([img, cap], i) => {
  const x = 0.95 + i * 3.1;
  phone(s, img, x, 1.85, 4.1, cap);
  num(s, x + 0.72, 6.15, String(i + 1), i === 3 ? C.accent1 : C.accent2, 0.4);
  if (i < 3) chevron(s, x + 2.4, 3.75, `step arrow ${i + 1}`);
  T(s, cap, { x: x - 0.3, y: 6.6, w: 2.55, h: 0.45, fontSize: 11, color: C.text1, align: "center" });
});
s.addNotes("Here is how. Once the app is installed, it quietly saves the verified hospitals near her and what each can do. With no signal, triage runs on the phone using the same rules as our server; we test that they give the same answer. She sees the nearest ready hospitals, with a call button, so she can go right away. Her request is saved on the phone, and the moment the signal returns, it is sent to the hospital automatically. No signal is a delay, not a dead end.");

s = light("Availability", "The hospital, offline", "The hospital keeps working too.");
card(s, "D_outbox.png", 0.8, 1.95, 7.6, 1800 / 2880, "Hospital screen with no signal");
point(s, 9.0, 2.0, 3.7, "Nothing is lost", "Accept, arrival and vitals are saved on the phone.", "1", 1.1);
point(s, 9.0, 3.25, 3.7, "Sent in order", "When the signal returns, in the order they happened.", "2", 1.1);
point(s, 9.0, 4.5, 3.7, "On time", "Vitals keep the time they were taken.", "3", 1.1);
point(s, 9.0, 5.5, 3.7, "Honest", "If another nurse already acted, it says so.", "4", 1.1);
s.addNotes("Hospitals lose signal too. So a nurse or doctor can keep working: accepting a referral, marking an arrival, taking vitals. Each one is saved on the phone and sent in order the moment the signal returns, and vitals keep the time they were actually taken. If someone else already acted on the same patient, the screen says so instead of hiding it.");

s = light("Availability", "Built for the phones people have", "Light enough for any phone, any network.");
[["6 KB", "Every verified hospital nearby, saved on the phone"], ["< 1 KB", "Sent per tap during triage"], ["228 KB", "The whole app, first time, compressed"], ["0", "App store downloads. It installs from the browser."]].forEach(([n, l], i) => {
  const x = 0.7 + i * 3.05;
  s.addShape(pres.shapes.LINE, { x, y: 2.3, w: 2.7, h: 0, line: { color: C.accent1, width: 2 }, objectName: `stat rule ${i + 1}` });
  T(s, n, { x, y: 2.55, w: 2.85, h: 1.3, fontSize: 52, bold: true, color: C.accent1 });
  T(s, l, { x, y: 3.95, w: 2.6, h: 1.0, fontSize: 16, color: C.text1 });
});
T(s, "Light and dark mode  ·  Large tap targets  ·  Pictures before words  ·  Works on a basic Android phone", { x: 0.7, y: 5.75, w: 11.9, h: 0.45, fontSize: 15, color: C.accent4 });
s.addNotes("And it is light. The saved list of every verified hospital nearby is about six kilobytes. Each tap during triage sends under one kilobyte. The whole app, the first time, is about 228 kilobytes compressed, smaller than a single photo on WhatsApp. And there is no app store: it installs straight from the browser, on a basic Android phone.");

// =====================================================================================================
// ADOPTION
// =====================================================================================================
pres.addSection({ title: "Adoption" });
s = light("Adoption", "Why hospitals join", "Hospitals get patients who arrive expected.");
point(s, 0.7, 2.0, 6.0, "Patients arrive expected", "Danger signs, symptoms and ETA before she walks in.", "1");
point(s, 0.7, 3.05, 6.0, "The right patient at the right door", "They are sent only the cases they said they can treat.", "2");
point(s, 0.7, 4.1, 6.0, "Insured and maternal patients find them", "“Accepts NHIA” and “Free maternal care” show on every suggestion.", "3");
point(s, 0.7, 5.15, 6.0, "Nothing to buy to start", "Free to receive referrals, on the phones staff already carry.", "4");
card(s, "D_coverage.png", 7.3, 2.1, 5.3, 500 / 2176, "Cost and coverage settings");
T(s, "The hospital admin sets cost and coverage once. Patients see it at the moment they choose where to go.", { x: 7.3, y: 3.6, w: 5.3, h: 0.9, fontSize: 14, color: C.accent4 });
card(s, "incoming.png", 7.3, 4.6, 3.6, 576 / 1094, "Incoming referral");
s.addNotes("Why would a hospital join? Because its patients arrive expected: danger signs, symptoms and ETA before she walks in. Because it is sent only the cases it said it can treat, so fewer patients turn up at the wrong door. Because insured and maternal patients can now find it: the hospital admin marks 'Accepts NHIA' and 'Free maternal care' once, and families see it at the moment they choose. And because there is nothing to buy to start. Receiving referrals is free, on the phones staff already carry.");

s = light("Adoption", "Who we build for", "Public first. Paid for by those who can.");
box(s, 0.7, 1.95, 5.85, 3.6, C.accent1, "public sector panel");
T(s, [{ text: "Public sector", options: { bold: true, fontSize: 24, color: C.background1, breakLine: true } }, { text: "Free, for good", options: { fontSize: 15, color: "CFE9DF", breakLine: true } },
  { text: "State ministries of health and primary health care boards", options: { bullet: true, fontSize: 15, color: C.background1, breakLine: true } },
  { text: "General hospitals, teaching hospitals and health centres", options: { bullet: true, fontSize: 15, color: C.background1, breakLine: true } },
  { text: "Works alongside the NHIA", options: { bullet: true, fontSize: 15, color: C.background1 } }],
  { x: 1.05, y: 2.2, w: 5.2, h: 3.2, paraSpaceAfter: 8 });
box(s, 6.78, 1.95, 5.85, 3.6, C.accent2, "private sector panel");
T(s, [{ text: "Private sector", options: { bold: true, fontSize: 24, color: C.background1, breakLine: true } }, { text: "Pays for extras", options: { fontSize: 15, color: "D7E6EA", breakLine: true } },
  { text: "Private hospitals and HMOs", options: { bullet: true, fontSize: 15, color: C.background1, breakLine: true } },
  { text: "Dashboards, links to their own systems, priority support", options: { bullet: true, fontSize: 15, color: C.background1, breakLine: true } },
  { text: "The same network, the same patients", options: { bullet: true, fontSize: 15, color: C.background1 } }],
  { x: 7.13, y: 2.2, w: 5.2, h: 3.2, paraSpaceAfter: 8 });
T(s, "Never a fee per referral. A patient in an emergency is never a sale.", { x: 0.7, y: 5.85, w: 11.9, h: 0.5, fontSize: 20, bold: true, color: C.text1 });
T(s, "Proposed model.", { x: 0.7, y: 6.35, w: 11.9, h: 0.35, fontSize: 12, color: C.accent4 });
s.addNotes("Who is it for? Public first. Most Nigerians, especially low and middle income families, get care from public hospitals and health centres, so for them and for state ministries of health, VITALIS is free. Private hospitals and HMOs pay for extras: dashboards, links to their own systems, priority support. Same network, same patients. And one rule we will not break: there is never a fee per referral. A patient in an emergency is never a sale.");

s = light("Adoption", "How it spreads", "Start where people already go first.");
[["Abeokuta pilot", "Chemists and hospitals in one city. Clinicians review the rules."], ["Ogun State", "With the state ministry of health and primary health care board."],
  ["South-West", "Yoruba and Pidgin, with voice prompts."], ["Nigeria", "Hausa and Igbo. Linked with the NHIA."]].forEach(([h, b], i) => {
  const x = 0.7 + i * 3.05;
  num(s, x, 2.15, String(i + 1));
  if (i < 3) s.addShape(pres.shapes.LINE, { x: x + 0.56, y: 2.38, w: 2.39, h: 0, line: { color: C.accent6, width: 2 }, objectName: `roadmap line ${i + 1}` });
  T(s, [{ text: h, options: { bold: true, fontSize: 19, color: C.text1, breakLine: true } }, { text: b, options: { fontSize: 14, color: C.accent4 } }], { x, y: 2.9, w: 2.75, h: 1.6, paraSpaceAfter: 4 });
});
box(s, 0.7, 4.9, 11.93, 1.3, C.accent5, "chemist first panel");
T(s, [{ text: "The chemist on the corner is our way in.  ", options: { bold: true, color: C.accent1 } },
  { text: "Every neighbourhood has one, people already trust them, and VITALIS shows them the good they do each month.", options: { color: C.text1 } }],
  { x: 1.0, y: 4.9, w: 11.4, h: 1.3, fontSize: 17, valign: "middle" });
s.addNotes("How does it spread? We start with a pilot in Abeokuta: chemists and hospitals in one city, with clinicians reviewing our rules. Then Ogun State, with the ministry of health and the primary health care board. Then the South-West, in Yoruba and Pidgin with voice prompts. Then Nigeria, in Hausa and Igbo, linked with the NHIA. And our way in is the chemist on the corner: every neighbourhood has one, people already trust them, and VITALIS shows them the good they do each month.");

// =====================================================================================================
// BENEFITS
// =====================================================================================================
pres.addSection({ title: "Benefits" });
s = dark("Benefits");
T(s, "What changes.", { x: 0.9, y: 2.4, w: 11.5, h: 1.4, fontSize: 72, bold: true, color: C.background1 });
T(s, "For families. For hospitals. For Nigeria.", { x: 0.9, y: 3.9, w: 11.5, h: 0.7, fontSize: 28, color: C.accent6 });
s.addNotes("So what changes? For families, for hospitals, and for Nigeria.");

s = light("Benefits", "The problems, solved", "Five problems. Five answers.");
const ANSWERS = [
  "Hospitals mark what they can do. Only those that can treat her are shown, freshest first.",
  "He triages and refers live, and sees who reached care.",
  "One VITALIS ID. History opens with her consent; allergies always travel.",
  "Hospitals are saved on the phone. Requests and hospital actions send when signal returns.",
  "NHIA and free maternal care are shown. Insured patients see covered hospitals first.",
];
PROBLEMS.forEach(([p], i) => {
  const y = 1.95 + i * 0.92;
  box(s, 0.7, y, 4.6, 0.76, C.background2, `problem row ${i + 1}`);
  T(s, [{ text: `0${i + 1}  `, options: { bold: true, color: C.accent3 } }, { text: p, options: { color: C.text1 } }], { x: 0.95, y, w: 4.2, h: 0.76, fontSize: 16, bold: true, valign: "middle" });
  s.addShape(pres.shapes.RIGHT_ARROW, { x: 5.45, y: y + 0.2, w: 0.5, h: 0.36, fill: { color: C.accent6 }, line: { type: "none" }, objectName: `answer arrow ${i + 1}` });
  box(s, 6.1, y, 6.53, 0.76, C.accent5, `answer row ${i + 1}`);
  T(s, ANSWERS[i], { x: 6.35, y, w: 6.1, h: 0.76, fontSize: 14, color: C.text1, valign: "middle" });
});
s.addNotes("Remember the five problems. Nobody knows who is ready: now hospitals mark what they can do, and only those that can treat her are shown, freshest first. The chemist refers blind: now he refers live and sees who reached care. Records stay behind: now one VITALIS ID carries her history, opened with her consent, and allergies always travel. Signal and power fail: now hospitals are saved on the phone and everything sends when the signal returns. Cost decides the door: now NHIA and free maternal care are shown, and insured patients see covered hospitals first.");

s = light("Benefits", "Who benefits", "Better for everyone in the room.");
[["Families", C.accent1, ["Know where to go, in three taps", "Their history follows them, on their terms", "Works with no signal, on any phone", "Free, with no account"]],
  ["Hospitals", C.accent2, ["Patients arrive expected and triaged", "Fewer patients at the wrong door", "Safer prescribing, with history from other hospitals", "Keep working when the network drops"]],
  ["Nigeria", C.text2, ["Faster care where delay costs lives, starting with mothers", "Chemists become a trusted front door", "Insurance and free care easier to use", "A clear view of where care is needed most"]]].forEach(([h, color, items], i) => {
  const x = 0.7 + i * 4.05;
  box(s, x, 1.95, 3.83, 0.85, color, `${h} header`);
  T(s, h, { x: x + 0.3, y: 1.95, w: 3.3, h: 0.85, fontSize: 22, bold: true, color: C.background1, valign: "middle" });
  box(s, x, 2.95, 3.83, 3.55, C.background2, `${h} list`);
  T(s, items.map((t, k) => ({ text: t, options: { bullet: { indent: 16 }, breakLine: k < items.length - 1 } })), { x: x + 0.3, y: 3.2, w: 3.3, h: 3.15, fontSize: 17, color: C.text1, paraSpaceAfter: 14 });
});
s.addNotes("For families: they know where to go in three taps, their history follows them on their terms, and it works with no signal, free, with no account. For hospitals: patients arrive expected, fewer turn up at the wrong door, prescribing is safer, and work continues when the network drops. And for Nigeria: faster care where delay costs lives, starting with mothers; chemists become a trusted front door; insurance and free care become easier to use; and for the first time, a clear view of where care is needed most.");

s = dark("Benefits");
T(s, "BY THE NUMBERS", { x: 0.9, y: 0.75, w: 6, h: 0.35, fontSize: 13, bold: true, color: C.accent6, charSpacing: 2 });
[["3", "taps to an emergency plan"], ["6 KB", "to work with no signal"], ["10 min", "a QR code lasts"], ["24 h", "a consent lasts"],
  ["9", "roles, one journey"], ["114", "automated tests"], ["< 1 KB", "per tap"], ["0", "fees per referral"]].forEach(([n, l], i) => {
  const x = 0.9 + (i % 4) * 3.0, y = 1.5 + Math.floor(i / 4) * 2.55;
  T(s, n, { x, y, w: 2.85, h: 1.25, fontSize: 52, bold: true, color: C.background1 });
  T(s, l, { x, y: y + 1.3, w: 2.7, h: 0.8, fontSize: 17, color: "A1A1A6" });
});
s.addNotes("By the numbers. Three taps to an emergency plan. Six kilobytes to work with no signal. A QR code that lasts ten minutes, and consent that lasts twenty-four hours. Nine roles, one journey. 114 automated tests. Under a kilobyte per tap. And zero fees per referral.");

// =====================================================================================================
// CLOSE
// =====================================================================================================
pres.addSection({ title: "Close" });
s = dark("Close");
s.addImage({ path: IMG("icon.png"), x: 0.9, y: 1.2, w: 0.9, h: 0.9, objectName: "VITALIS icon", altText: "VITALIS icon" });
T(s, [{ text: "From “something is wrong”", options: { breakLine: true } }, { text: "to “a hospital is ready for you.”", options: { color: C.accent6 } }],
  { x: 0.9, y: 2.5, w: 8.2, h: 2.0, fontSize: 38, bold: true, color: C.background1, objectName: "closing line" });
T(s, "Try it now: vitalis.olamide.cloud", { x: 0.9, y: 4.8, w: 8.2, h: 0.6, fontSize: 24, color: "A1A1A6" });
box(s, 9.4, 1.9, 3.2, 3.2, C.background1, "QR panel");
s.addImage({ path: IMG("qr.png"), x: 9.6, y: 2.1, w: 2.8, h: 2.8, objectName: "QR code to vitalis.olamide.cloud", altText: "QR code linking to vitalis.olamide.cloud" });
T(s, "Scan to open VITALIS", { x: 9.4, y: 5.3, w: 3.2, h: 0.4, fontSize: 14, color: "A1A1A6", align: "center" });
s.addNotes("VITALIS. From 'something is wrong' to 'a hospital is ready for you'. Scan the code and try it now. Thank you.");

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
