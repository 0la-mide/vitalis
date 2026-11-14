# ruff: noqa: ISC004  (long guide text is wrapped across lines on purpose)
"""VITALIS user and test guide (PDF).

Built by the seed next to DEMO_LOGINS.pdf, so the sign-in details inside always match the server that made it.
The repository is public: this file holds no passwords; they are filled in at build time and the PDF is gitignored.
Screenshots in ./img are synthetic demo data.
"""

from datetime import date
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

IMG = Path(__file__).parent / "img"
INK = (20, 32, 28)
PRIMARY = (15, 92, 74)
CALM = (19, 78, 94)
MUTED = (88, 100, 96)
MINT = (238, 246, 243)
LINE = (222, 228, 225)
ROLE_ORDER = ["facility_admin", "receptionist", "nurse", "doctor", "lab", "radiology"]
ROLE_LABEL = {"facility_admin": "Hospital admin", "receptionist": "Reception", "nurse": "Nurse", "doctor": "Doctor",
              "lab": "Lab", "radiology": "Radiology", "pending nurse": "Nurse (pending)"}


def _t(s: str) -> str:
    """Core PDF fonts are Latin-1 only."""
    for a, b in {"—": "-", "–": "-", "→": "->", "’": "'", "‘": "'", "“": '"', "”": '"', "…": "...",
                 "≤": "<=", "≥": ">=", "✓": "", "₦": "N"}.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


class Guide(FPDF):
    title_text = "VITALIS user & test guide"

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, _t(self.title_text), align="L")
        self.cell(0, 6, _t("Synthetic demo data only"), align="R")
        self.ln(9)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_font("helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"{self.page_no()}", align="C")

    # ---------- building blocks ----------
    def h1(self, text: str, new_page: bool = True):
        if new_page:
            self.add_page()
        self.set_font("helvetica", "B", 20)
        self.set_text_color(*PRIMARY)
        self.multi_cell(0, 10, _t(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_draw_color(*PRIMARY)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y(), self.l_margin + 24, self.get_y())
        self.ln(4)

    def h2(self, text: str):
        self.ensure(22)
        self.ln(2)
        self.set_font("helvetica", "B", 13)
        self.set_text_color(*INK)
        self.multi_cell(0, 7, _t(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def p(self, text: str, size: float = 10.5, color=INK):
        self.set_font("helvetica", "", size)
        self.set_text_color(*color)
        self.multi_cell(0, size * 0.52, _t(text), markdown=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def steps(self, items: list[str]):
        self.set_font("helvetica", "", 10.5)
        for i, s in enumerate(items, 1):
            self.ensure(10)
            self.set_text_color(*PRIMARY)
            self.set_font("helvetica", "B", 10.5)
            self.cell(7, 5.6, f"{i}.")
            self.set_text_color(*INK)
            self.set_font("helvetica", "", 10.5)
            self.multi_cell(0, 5.6, _t(s), markdown=True, new_x="LMARGIN", new_y="NEXT")
            self.ln(0.8)
        self.ln(1)

    def bullets(self, items: list[str], size: float = 10.5):
        for s in items:
            self.ensure(8)
            self.set_font("helvetica", "B", size)
            self.set_text_color(*PRIMARY)
            self.cell(5, size * 0.53, "-")
            self.set_font("helvetica", "", size)
            self.set_text_color(*INK)
            self.multi_cell(0, size * 0.53, _t(s), markdown=True, new_x="LMARGIN", new_y="NEXT")
            self.ln(0.6)
        self.ln(1)

    def note(self, text: str, tone=CALM, fill=(231, 242, 244)):
        self.ensure(16)
        self.set_fill_color(*fill)
        self.set_draw_color(*tone)
        self.set_text_color(*INK)
        self.set_font("helvetica", "", 10)
        y = self.get_y()
        self.multi_cell(0, 5.2, _t(text), markdown=True, fill=True, padding=(3, 4, 3, 6), new_x="LMARGIN",
                        new_y="NEXT")
        self.set_line_width(1.2)
        self.line(self.l_margin, y, self.l_margin, self.get_y())
        self.ln(3)

    def ensure(self, h: float):
        if self.get_y() + h > self.h - self.b_margin:
            self.add_page()

    def phones(self, shots: list[tuple[str, str]]):
        """Up to three phone screenshots side by side, each with a caption."""
        w, gap = 54, 9
        h = w * 974 / 450
        self.ensure(h + 14)
        x0, y = self.l_margin + (self.epw - (len(shots) * w + (len(shots) - 1) * gap)) / 2, self.get_y()
        for i, (img, cap) in enumerate(shots):
            x = x0 + i * (w + gap)
            self.image(str(IMG / img), x=x, y=y, w=w, h=h)
            self.set_draw_color(*LINE)
            self.set_line_width(0.3)
            self.rect(x, y, w, h)
            self.set_xy(x, y + h + 1.5)
            self.set_font("helvetica", "", 8.5)
            self.set_text_color(*MUTED)
            self.multi_cell(w, 4, _t(cap), align="C")
        self.set_y(y + h + 12)

    def screen(self, img: str, cap: str, w: float = 170):
        h = w * 529 / 800
        self.ensure(h + 10)
        x, y = self.l_margin + (self.epw - w) / 2, self.get_y()
        self.image(str(IMG / img), x=x, y=y, w=w, h=h)
        self.set_draw_color(*LINE)
        self.set_line_width(0.3)
        self.rect(x, y, w, h)
        self.set_xy(self.l_margin, y + h + 1.5)
        self.set_font("helvetica", "", 8.5)
        self.set_text_color(*MUTED)
        self.multi_cell(0, 4, _t(cap), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def table(self, head: list[str], rows: list[list[str]], widths: list[float], size: float = 9.5):
        self.set_font("helvetica", "", size)
        self.set_text_color(*INK)
        heads = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=PRIMARY)
        with self.table_ctx(widths, heads) as t:
            r = t.row()
            for h in head:
                r.cell(_t(h))
            for row in rows:
                r = t.row()
                for c in row:
                    r.cell(_t(c))
        self.ln(3)

    def table_ctx(self, widths, heads):
        return super().table(col_widths=widths, headings_style=heads, line_height=6, first_row_as_headings=True,
                             cell_fill_color=MINT, cell_fill_mode="ROWS", borders_layout="HORIZONTAL_LINES",
                             text_align="LEFT")

    def tests(self, code: str, title: str, setup: str, steps: list[tuple[str, str]]):
        """A test case: numbered actions with the expected result and an empty Pass/Fail column."""
        self.ensure(30)
        self.set_font("helvetica", "B", 11.5)
        self.set_text_color(*PRIMARY)
        self.cell(14, 7, code)
        self.set_text_color(*INK)
        self.multi_cell(0, 7, _t(title), new_x="LMARGIN", new_y="NEXT")
        if setup:
            self.p(f"__Setup:__ {setup}", size=9.5, color=MUTED)
        heads = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=CALM)
        self.set_font("helvetica", "", 9)
        self.set_text_color(*INK)
        with super().table(col_widths=[8, 74, 74, 18], headings_style=heads, line_height=5, first_row_as_headings=True,
                           cell_fill_color=(246, 249, 248), cell_fill_mode="ROWS",
                           borders_layout="HORIZONTAL_LINES", text_align="LEFT") as t:
            r = t.row()
            for h in ("#", "Do this", "You should see", "Pass?"):
                r.cell(h)
            for i, (do, see) in enumerate(steps, 1):
                r = t.row()
                r.cell(str(i))
                r.cell(_t(do))
                r.cell(_t(see))
                r.cell("[  ]")
        self.ln(4)


def build_user_guide(out: Path, *, password: str, base_url: str, logins: list[tuple[str, str, str]],
                     patients: list[tuple[str, str, str]]) -> Path:
    """logins: (who, email, status) from the seed; patients: (name, vitalis_id, recovery_code)."""
    url = base_url.rstrip("/")
    pdf = Guide(format="A4")
    pdf.set_margins(18, 14, 18)
    pdf.set_auto_page_break(True, margin=16)
    pdf.set_title("VITALIS user and test guide")

    # ---------------- cover ----------------
    pdf.add_page()
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(0, 0, pdf.w, 112, style="F")
    pdf.set_xy(18, 38)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 34)
    pdf.cell(0, 14, "VITALIS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 15)
    pdf.cell(0, 9, _t("From \"something is wrong\" to \"a hospital is ready for you\""), new_x="LMARGIN",
             new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 10, "User & test guide", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(124)
    pdf.set_text_color(*INK)
    pdf.p(f"**Live app:** {url}", size=12)
    pdf.p(f"**Staff sign-in:** {url}/auth/login", size=12)
    pdf.p(f"**Edition:** {date.today():%d %B %Y}  ·  ITDC 2026 hackathon build", size=12)
    pdf.ln(4)
    pdf.note("Everything in VITALIS is **synthetic demo data**: the people, hospitals, phone numbers and records are "
             "made up. Do not enter real patient information.")
    pdf.ln(2)
    pdf.h2("What is inside")
    pdf.bullets([
        "**1. Sign-in details** - every working account and the demo patients.",
        "**2. Before you start** - phones, alerts, dark mode, languages.",
        "**3. The family** - emergency in a few taps, hospital confirmation, directions.",
        "**4. My health record** - the patient's record, sharing by QR, who looked.",
        "**5. The chemist (frontline worker)** - triage a walk-in, vitals, referrals.",
        "**6. The hospital** - reception, nurse, doctor and VITALIS AI, lab and radiology, hospital admin.",
        "**7. Network admin** - verification, audit log.",
        "**8. Full test plan** - step-by-step checks with what you should see, and a Pass box.",
        "**9. Troubleshooting** and known limits.",
    ])

    # ---------------- 1. sign-in details ----------------
    pdf.h1("1. Sign-in details")
    pdf.p(f"Staff, chemists and admins sign in at **{url}/auth/login** with an email and password. Patients never "
          "need an account.")
    pdf.set_fill_color(*MINT)
    pdf.set_draw_color(*PRIMARY)
    pdf.set_line_width(0.5)
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(*INK)
    pdf.cell(0, 13, _t(f"   Password for every account:   {password}"), border=1, fill=True, new_x="LMARGIN",
             new_y="NEXT")
    pdf.ln(3)
    pdf.p("These details were created when the demo data was last reset on this server. Resetting the demo data "
          "(the reset-demo option of deploy.sh) makes a new password and a new copy of this guide, unless DEMO_PASSWORD is set.",
          size=9.5, color=MUTED)

    general, by_fac = [], {}
    for who, email, status in logins:
        if " - " in who:
            fac, role = who.rsplit(" - ", 1)
            by_fac.setdefault(fac, {})[role] = (email, status)
        else:
            general.append((who, email, status))

    pdf.h2("Start with these (the main demo story)")
    central = by_fac.get("Abeokuta Central Hospital (Demo)", {})
    sapon = by_fac.get("Sapon Mother & Child Hospital (Demo)", {})
    key = [["Network admin", e, "Verifies hospitals and chemists, audit log"] for w, e, s in general
           if "admin" in w.lower()]
    key += [[w.replace("Frontline worker", "Chemist"), e, "Walk-in triage, vitals, referrals"] for w, e, s in general
            if "worker" in w.lower() and s == "approved"]
    for role, what in [("receptionist", "Incoming referrals, confirm arrival, walk-ins"),
                       ("nurse", "Vital signs"), ("doctor", "Accept/decline, record, VITALIS AI, prescribe, orders"),
                       ("lab", "Sample collected, results, verify"), ("radiology", "Scan reports, verify"),
                       ("facility_admin", "Approve staff, service availability")]:
        if role in central:
            key.append([f"Central - {ROLE_LABEL[role]}", central[role][0], what])
    if "doctor" in sapon:
        key.append(["Sapon - Doctor", sapon["doctor"][0], "Second hospital (accepts the demo case)"])
    pdf.table(["Who", "Email", "Use it for"], key, [38, 72, 64], size=9)

    pdf.h2("Demo patients (no password)")
    pdf.p("On a phone open **My health record** and tap the patient's name under __Demo: open a patient's phone__. "
          "Or restore with the VITALIS ID and recovery code below (a recovery code works once; restoring gives a new "
          "one).", size=10)
    pdf.table(["Patient", "VITALIS ID", "Recovery code"], [list(p) for p in patients], [70, 50, 54], size=9.5)

    pdf.h2("Accounts for testing verification (pending)")
    pending = [[w, e, "Shows the status page only, until approved"] for w, e, s in general if s != "approved"]
    for fac, roles in by_fac.items():
        for role, (email, status) in roles.items():
            if status != "approved":
                pending.append([f"{fac.replace(' (Demo)', '')} - {ROLE_LABEL.get(role, role)}", email,
                                "Shows the status page only, until approved"])
    pdf.table(["Who", "Email", "Note"], pending, [62, 70, 42], size=9)

    pdf.h2("Every hospital account")
    pdf.p("Each hospital has the same six roles. Email = **role.code@vitalis.demo**, for example "
          "doctor.central@vitalis.demo. Roles: **facilityadmin** (hospital admin), **receptionist**, **nurse**, "
          "**doctor**, **lab**, **radiology**.", size=10)
    rows = []
    for fac in sorted(by_fac):
        doc = by_fac[fac].get("doctor")
        if doc and doc[1] == "approved":
            code = doc[0].split("@")[0].split(".", 1)[1]
            rows.append([fac.replace(" (Demo)", ""), code, f"receptionist.{code}@vitalis.demo",
                         f"doctor.{code}@vitalis.demo"])
    pdf.table(["Hospital", "Code", "Reception", "Doctor"], rows, [56, 22, 50, 46], size=8.5)

    # ---------------- 2. before you start ----------------
    pdf.h1("2. Before you start")
    pdf.h2("Use two devices")
    pdf.p("VITALIS is about people talking to each other, so test with **two devices or two browsers**: a phone for "
          "the family or chemist, and a laptop for the hospital. In one browser, each sign-in replaces the last one, "
          "so use a private/incognito window or a second browser for a second staff account.")
    pdf.h2("Install it like an app (optional, recommended)")
    pdf.bullets([
        "**Android (Chrome):** menu (three dots) -> __Install app__ or __Add to Home screen__.",
        "**iPhone (Safari):** Share -> __Add to Home Screen__. Open VITALIS from the new icon.",
        "Once installed it opens full screen and shows an offline page when there is no network.",
    ])
    pdf.h2("Alerts on the phone")
    pdf.p("Tap **Get alerts on this phone** (on the family's referral page, the chemist's __My referrals__, or the "
          "hospital's __Incoming__). Allow notifications when asked. Alerts then arrive even with VITALIS closed: "
          "hospital ready, finding another hospital, not arrived yet, and new referrals for hospital staff. "
          "On iPhone, alerts only work after __Add to Home Screen__. Alerts never show symptoms on the lock screen.")
    pdf.h2("Light and dark mode")
    pdf.p("The moon/sun button (top of the patient home, staff sidebar, chemist header, sign-in page) switches "
          "between light and dark. Both use the same calm colours. Until you choose, it follows the phone.")
    pdf.h2("Languages")
    pdf.p("English is available now. Pidgin, Yoruba, Hausa and Igbo show as __coming soon__.")
    pdf.h2("Location")
    pdf.p("VITALIS asks for your location to rank nearby hospitals. If you say no (or on plain http), it uses an "
          "approximate location and you can pick your area. For the demo, Abeokuta South matches the demo hospitals.")

    # ---------------- 3. the family ----------------
    pdf.h1("3. The family: get the right hospital, fast")
    pdf.p("No account, no typing. Every tap updates the hospital bar at the bottom (nearby / can handle this / ready "
          "now). Danger signs stop the questions at once and show the emergency screen.")
    pdf.steps([
        f"Open **{url}** on a phone.",
        "Tap what is happening, e.g. **Pregnancy problem**. (For anything else tap **Something else**, then who is "
        "sick: man, woman, pregnant woman, child, older person.)",
        "Tap **where** on the body. Women's bodies show breasts and the chest is labelled __Chest & breasts__.",
        "Tap **what you see or feel**. One tap moves you on; no Next button.",
        "If it is an emergency you see **THIS IS AN EMERGENCY**, a **Call 112** button and the best hospitals with "
        "reasons. Nearby hospitals are alerted straight away.",
        "Tap **Send to this hospital**. Show the VITALIS ID at reception.",
    ])
    pdf.phones([("p1_home.jpg", "1. What is happening?"), ("p2_body.jpg", "2. Where is the problem? (pregnant)"),
                ("p3_symptoms.jpg", "3. What do you see or feel?")])
    pdf.phones([("p4_emergency.jpg", "4. Emergency: call 112, best hospitals"),
                ("p5_waiting.jpg", "5. Waiting for the hospital"), ("p6_accepted.jpg", "6. Go now: they are ready")])
    pdf.p("When the hospital accepts: **Go now**, directions, a call button and what to bring. If it declines, "
          "VITALIS moves the request to the next best hospital automatically. If the family gave a phone number they "
          "also get an SMS.")

    # ---------------- 4. my health record ----------------
    pdf.h1("4. My health record")
    pdf.p("From the patient home: **My health record**. Four tabs:")
    pdf.bullets([
        "**Record** - allergies, conditions, medicines, family history; each says which hospital recorded it and when.",
        "**Visits** - every visit at every hospital: vital signs, verified results, signed notes, prescriptions.",
        "**Share** - pick a hospital (or any verified hospital) and __Everything__ or __Summary only__, then **Show my QR "
        "code**. The hospital scans it with a phone camera. The code works once and expires in 10 minutes; access "
        "lasts 24 hours.",
        "**Who looked** - who can see the record now (with **Stop**), and every view and request.",
    ])
    pdf.p("When a doctor taps __Ask the patient to share__, the patient's phone shows a banner with **Allow** / **Don't "
          "allow**. Without permission a hospital sees only its own visits, plus allergies (always shown for safety).")
    pdf.phones([("p7_record.jpg", "Record: each entry shows where it came from"),
                ("p8_share.jpg", "Share: one-time QR, 10 minutes")])

    # ---------------- 5. chemist ----------------
    pdf.h1("5. The chemist (frontline worker)")
    pdf.p("For chemists, pharmacists, CHEWs and midwives. Sign in as **Chemist 1** (see section 1).")
    pdf.steps([
        "**New walk-in**: optionally type the family's phone (for SMS alerts), then triage on the patient's behalf "
        "with the same taps as the family.",
        "Add **vital signs** (BP, pulse, temperature, SpO2, breathing rate, weight). Danger values raise a red flag.",
        "Send to the suggested hospital. Give the family the **recovery slip** (VITALIS ID + code).",
        "**My referrals** shows each referral live: pending, accepted, declined -> next hospital, arrived, overdue.",
    ])
    pdf.phones([("w1_worker.jpg", "New walk-in")])
    pdf.p("The chemist sees the type of care and danger signs, never disease likelihoods.", size=10, color=MUTED)

    # ---------------- 6. hospital ----------------
    pdf.h1("6. The hospital")
    pdf.p("Each role sees its own screens. The left sidebar shows the patient's journey: Reception -> Nursing -> "
          "Doctor -> Lab & imaging.")
    pdf.h2("Reception")
    pdf.bullets([
        "**Incoming referrals** - live: symptoms, danger signs, ETA. A doctor or nurse accepts or declines (decline "
        "needs a reason; the family is moved to the next hospital).",
        "When the patient arrives: **Confirm arrival & open encounter**. Everything the chemist or family entered "
        "comes with them; nothing is typed twice.",
        "Walk-ins without a referral: register them at reception.",
        "**Service availability** - one tap per service (available / limited / unavailable). It stamps the time; "
        "families see how fresh it is.",
    ])
    pdf.screen("h1_incoming.jpg", "Incoming referrals at the hospital, updating live")
    pdf.h2("Nurse")
    pdf.p("**Patients in the facility** -> the patient in __Nursing__ -> record vital signs. New readings show next to the "
          "chemist's earlier ones with a trend arrow; dangerous values are flagged. Corrections keep the original.")
    pdf.h2("Doctor")
    pdf.steps([
        "Open the patient from __Patients in the facility__. The **Patient record** shows allergies and history with the "
        "hospital that recorded each item.",
        "**Records from other hospitals** stays locked until the patient shares: tap **Ask the patient to share** (or "
        "scan their QR).",
        "Tap **Run VITALIS AI**: red flags, a summary, possible conditions ranked with the evidence behind each, safety "
        "alerts from the record, the team's risk models and trends. The AI never gives doses; the doctor decides.",
        "**Prescribe**: type a medicine and tap **Check safety**. A conflict with the record is blocked; prescribing "
        "anyway needs a reason (audited).",
        "**Order tests**, write and **sign** the note, then **Decide disposition** (discharge, admit, refer).",
    ])
    pdf.screen("h2_ai.jpg", "VITALIS AI: red flag and a safety alert from another hospital's record")
    pdf.screen("h3_models.jpg", "The team's risk models: band, model score and which inputs were measured")
    pdf.screen("h4_prescribe.jpg", "Safety check blocks a medicine that conflicts with the recorded allergy")
    pdf.h2("Lab and radiology")
    pdf.bullets([
        "**Lab** sees blood and urine tests only: **Sample collected** -> enter the result (numbers are checked "
        "against reference ranges and flagged H/L) -> **Verify**.",
        "**Radiology** sees scans and X-rays only: write the report -> **Verify**.",
        "Only verified results go back to the doctor. When all are verified, the patient returns to the Doctor column.",
    ])
    pdf.screen("h5_lab.jpg", "Lab worklist: the X-ray in the same order went to radiology")
    pdf.h2("Hospital admin")
    pdf.p("Approves staff who registered for this hospital (__Staff__), and keeps __Service availability__ up to date.")

    # ---------------- 7. network admin ----------------
    pdf.h1("7. Network admin")
    pdf.bullets([
        "**Verifications** - new hospitals and chemists with their licence documents: approve, reject (with reason) "
        "or suspend. A hospital is never suggested to families until approved.",
        "**Audit & governance** - every record view, QR use, decision and AI action, with filters.",
        "**Network overview** - counts only (no patient names): triage, red flags, referrals, arrival rate, overdue.",
    ])
    pdf.screen("a1_verify.jpg", "Verification queue with documents")

    # ---------------- 8. test plan ----------------
    pdf.h1("8. Full test plan")
    pdf.p("Work through these in order on the live app. Tick **Pass?** as you go and write notes beside anything "
          "odd. __Family phone__ = a phone (or private window) with no sign-in. Emails are in section 1.")

    pdf.tests("T1", "Emergency: family to hospital in a few taps", "Family phone + laptop signed in as Central "
              "Reception (Incoming page open).", [
        ("Family: tap Pregnancy problem -> Private parts / groin -> Heavy bleeding.",
         "Emergency screen after 3 taps: Call 112, hospitals with reasons. Time it: under 15 seconds."),
        ("Check the hospital list.", "Abeokuta Central and Sapon offered. Ibara Family Clinic (closest, but no obstetrician) is not offered."),
        ("Tap Send to this hospital (Central).", "Waiting for the hospital... with VITALIS ID and map."),
        ("Laptop: Incoming.", "The new referral appears by itself with the danger message."),
        ("Sign in as Central Doctor, accept it.", "Family phone switches to Go now within ~3 s: directions, call, "
                                                  "what to bring."),
    ])
    pdf.tests("T2", "Hospital declines -> next hospital", "As T1, but do not accept.", [
        ("Central Doctor: Decline without a reason.", "Refused: a reason is required."),
        ("Decline with reason 'Theatre busy'.", "Family phone: Central declined, request moved to the next hospital "
                                               "(e.g. Sapon). The reason is not shown to the family."),
        ("Sapon Doctor: accept.", "Family phone shows Go now for Sapon."),
    ])
    pdf.tests("T3", "Non-urgent path, taps only", "Family phone.", [
        ("Something else -> Man -> Head -> Headache -> pick a face -> Today.",
         "Advice level (e.g. go today / see a clinic) and best hospitals. No disease names anywhere."),
        ("Something else -> Woman -> chest.", "Label reads Chest & breasts; breast cards are offered."),
        ("Something else -> Pregnant woman -> upper belly.", "No 'swollen belly' option."),
    ])
    pdf.tests("T4", "Chemist walk-in", "Phone signed in as Chemist 1.", [
        ("New walk-in: family phone +2348000000077, Can't breathe.", "Red flag and hospitals."),
        ("Add vitals: SpO2 86.", "Flagged as dangerous."),
        ("Send to the suggested hospital.", "Recovery slip with VITALIS ID and code."),
        ("My referrals.", "The referral shows live status."),
    ])
    pdf.tests("T5", "Arrival to discharge, no re-typing", "Laptop: Central Reception, then Nurse, then Doctor.", [
        ("Reception: Confirm arrival on an accepted referral.", "Encounter opens with symptoms and chemist vitals."),
        ("Nurse: record vitals.", "Shown next to earlier readings with trend arrows."),
        ("Doctor: write and sign a note; Decide disposition (e.g. discharged).", "Timeline lists every step with time "
                                                                                 "and name; referral shows Completed."),
    ])
    pdf.tests("T6", "Doctor, VITALIS AI and safe prescribing", "Central Doctor -> Patients -> the visit in the Doctor "
              "column (headache, blurred vision, thirst).", [
        ("Run VITALIS AI.", "BP red flag; uncontrolled hypertension; possible new diabetes; model cards with band and "
                            "model score; 'Do not give Hydrochlorothiazide' citing Ogun Teaching Hospital."),
        ("Prescribe Hydrochlorothiazide -> Check safety.", "Blocked; needs a reason to override."),
        ("Prescribe Lisinopril, 10 mg once daily.", "Prescribed; joins her medicines."),
        ("Reject the AI draft without a reason; then Accept and draft note.", "Reject needs a reason; accept puts the "
                                                                              "text into the draft note."),
    ])
    pdf.tests("T7", "Lab and radiology", "Doctor on any visit; then Central Lab and Central Radiology.", [
        ("Doctor: order Full blood count and Chest X-ray.", "Patient moves to Investigations."),
        ("Lab worklist.", "Only the blood test. Tap Sample collected, enter values, Save, then Verify."),
        ("Radiology worklist.", "Only the X-ray. Write the report, Save, Verify."),
        ("Doctor.", "Both results verified; patient back in the Doctor column."),
    ])
    pdf.tests("T8", "Shared record and consent", "Family phone: My health record -> Mrs. Folake Adewale. Laptop: "
              "Central Doctor on Folake's visit.", [
        ("Doctor: look at Records from other hospitals.", "Locked: 2 visits at other hospitals are private. Allergy "
                                                          "still shown."),
        ("Tap Ask the patient to share. Phone: Allow.", "Doctor sees Lafenwa and Ogun Teaching visits within ~3 s; "
                                                        "VITALIS AI now uses 3 earlier visits."),
        ("Phone: Who looked -> Stop.", "Doctor's view locks again."),
        ("Phone: Share -> Show my QR code. Open the code on the doctor's device.", "Record shared, straight to the "
                                                                                  "visit. Opening it again: already "
                                                                                  "used."),
    ])
    pdf.tests("T9", "Alerts and SMS", "Live HTTPS site; phone with VITALIS installed (iPhone: Add to Home Screen).", [
        ("Family referral page: Get alerts on this phone. Allow. Close the app.", "Button reads Alerts on."),
        ("Hospital accepts the referral.", "Phone shows 'Hospital is ready' with the app closed."),
        ("Hospital staff: Incoming -> Get alerts. Send a new referral.", "'New referral' notification."),
        ("If an SMS provider is set up and a family phone was given.", "SMS on accept / decline / overdue."),
    ])
    pdf.tests("T10", "Registration and verification", "Network admin, a pending account, a new browser.", [
        ("Sign in as the pending facility admin (section 1).", "Status page only; cannot reach work screens."),
        ("Network admin -> Verifications: open the licence PDF, Approve Asero.", "Asero appears in hospital matching."),
        ("Register a new staff member at /auth/register for Central.", "Pending until Central's hospital admin "
                                                                       "approves under Staff."),
    ])
    pdf.tests("T11", "Overdue patient", "An accepted referral where the patient does not arrive.", [
        ("Wait past ETA + 30 minutes (or ask the developer to run make overdue-now).",
         "Referral turns Overdue for family, chemist and hospital; alert/SMS sent if set up."),
    ])
    pdf.tests("T12", "Security spot checks", "Two hospital accounts.", [
        ("Nurse tries to prescribe or accept (no buttons).", "Not possible for a nurse."),
        ("Sapon staff opens a Central patient link.", "Not found (each hospital sees only its own patients)."),
        ("Patient record without consent.", "Other hospitals' visits stay hidden; every view is in Who looked."),
    ])
    pdf.tests("T13", "Look and feel", "Any device.", [
        ("Tap the moon/sun button.", "Switches light/dark; remembered after reload."),
        ("Open the language menu.", "English selectable; others marked coming soon."),
        ("Install the app; turn on airplane mode; open it.", "Offline page instead of a browser error."),
    ])

    # ---------------- 9. troubleshooting ----------------
    pdf.h1("9. Troubleshooting and known limits")
    pdf.bullets([
        "**Can't sign in** - check the email in section 1 and the password at the top of that page. If the demo data "
        "was reset after this guide was made, use the newest copy of this guide.",
        "**Signed in as the wrong person** - one browser holds one staff sign-in at a time. Use a private window or "
        "another browser for a second account.",
        "**No alerts** - notifications must be allowed for the site; on iPhone the app must be added to the Home "
        "Screen; alerts need the live https site.",
        "**No SMS** - texts are only sent when an SMS provider (Termii or BulkSMS Nigeria) is set up on the server.",
        "**Location wrong** - allow location, or pick your area from the list.",
        "**A hospital is missing from suggestions** - it may lack a service that the case needs (e.g. no obstetrician "
        "for pregnancy bleeding), be unverified, or be marked unavailable. The reasons are shown.",
    ])
    pdf.h2("Known limits of this demo build")
    pdf.bullets([
        "Pidgin, Yoruba, Hausa and Igbo text and voice prompts are coming soon.",
        "The clinical rules and medicine-safety list are marked __needs clinical review__.",
        "The team's risk models are not yet validated on Nigerian patients; they show bands, not diagnoses.",
        "There is no in-app QR scanner; staff scan with the phone camera.",
    ])
    pdf.ln(2)
    pdf.note("VITALIS supports decisions; it does not diagnose. Clinicians make and own every clinical decision.")

    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    return out
