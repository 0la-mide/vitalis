"""One page: VITALIS and the NHIA (formerly NHIS), complementary, never competing.

Run: cd backend && uv run python ../pitch/onepager/build.py   -> pitch/VITALIS-and-NHIA.pdf
"""
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

HERE = Path(__file__).resolve().parent
ICON = HERE.parent / "film" / "assets" / "brand" / "icon.png"
OUT = HERE.parent / "VITALIS-and-NHIA.pdf"
GREEN, TEAL, INK, MUTED, MINT, PAPER = (15, 92, 74), (19, 78, 94), (20, 32, 28), (75, 90, 85), (238, 246, 243), (246, 248, 247)


def t(s: str) -> str:
    for a, b in {"—": "-", "–": "-", "’": "'", "“": '"', "”": '"', "·": "-", "→": "->"}.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


pdf = FPDF(format="A4")
pdf.set_auto_page_break(False)
pdf.set_margins(16, 14, 16)
pdf.add_page()
W = pdf.w - 32

# header band
pdf.set_fill_color(*GREEN)
pdf.rect(0, 0, pdf.w, 40, style="F")
pdf.image(str(ICON), x=16, y=10, w=20, h=20)
pdf.set_xy(41, 10)
pdf.set_text_color(255, 255, 255)
pdf.set_font("helvetica", "B", 21)
pdf.cell(0, 9, "VITALIS and the NHIA", new_x="LMARGIN", new_y="NEXT")
pdf.set_x(41)
pdf.set_font("helvetica", "", 11.5)
pdf.cell(0, 7, t("Two halves of getting care in Nigeria"), new_x="LMARGIN", new_y="NEXT")

pdf.set_y(47)
pdf.set_text_color(*INK)
pdf.set_font("helvetica", "B", 12.5)
pdf.multi_cell(W, 6.6, t("The NHIA helps Nigerians pay for care. VITALIS helps them reach the right care, fast. "
                         "One makes care affordable; the other makes it reachable in the moment it is needed."),
               align="L", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)

# two columns
colw, gap, y0 = (W - 8) / 2, 8, pdf.get_y()


def column(x, title, sub, color, items):
    pdf.set_xy(x, y0)
    pdf.set_fill_color(*color)
    pdf.rect(x, y0, colw, 1.6, style="F")
    pdf.set_xy(x, y0 + 4)
    pdf.set_font("helvetica", "B", 12.5)
    pdf.set_text_color(*color)
    pdf.cell(colw, 6, t(title), new_x="LEFT", new_y="NEXT")
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(colw, 5, t(sub), new_x="LEFT", new_y="NEXT")
    pdf.ln(1)
    pdf.set_text_color(*INK)
    for it in items:
        pdf.set_x(x)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*color)
        pdf.cell(4, 5.2, "-")
        pdf.set_text_color(*INK)
        pdf.set_font("helvetica", "", 10.5)
        pdf.multi_cell(colw - 4, 5.6, t(it), markdown=True, align="L", new_x="LEFT", new_y="NEXT")
        pdf.ln(1.4)
    return pdf.get_y()


ya = column(16, "The NHIA (formerly NHIS)", "National Health Insurance Authority", TEAL, [
    "Nigeria's national health insurance body. The **NHIA Act 2022** turned the NHIS into an Authority with a wider "
    "mandate.",
    "Makes **health insurance mandatory**, the path to universal health coverage.",
    "Created a **Vulnerable Group Fund** so people who cannot pay are still covered.",
    "Pools funds and **pays for covered care** at accredited health facilities.",
    "Answers: **\"How will my care be paid for?\"**",
])
yb = column(16 + colw + gap, "VITALIS", "Healthcare coordination platform", GREEN, [
    "**Three taps** from \"something is wrong\" to an emergency plan, with no account.",
    "Suggests only **hospitals that can treat** the case, and alerts them before the patient arrives.",
    "**Live referrals**: the hospital accepts on its screen; the family gets directions, an alert and an SMS.",
    "One **VITALIS ID** per person: a shared record that opens **only with the patient's consent**.",
    "**Works with no signal**: the nearest ready hospitals are saved on the phone.",
    "Answers: **\"Where do I go right now, and are they ready?\"**",
])
pdf.set_y(max(ya, yb) + 3)

# side by side table
pdf.set_font("helvetica", "B", 12)
pdf.set_text_color(*INK)
pdf.cell(0, 7, "Side by side", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("helvetica", "", 10)
pdf.set_fill_color(*MINT)
heads = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=GREEN)
rows = [
    ("Role", "Financial protection", "Care coordination"),
    ("Main question", "Who pays for care?", "Who can treat this, right now?"),
    ("Used by", "Enrollees, health facilities, HMOs", "Families, chemists, hospital staff"),
    ("Identity", "NHIA enrolment number", "VITALIS ID, can carry the NHIA number"),
    ("When it matters", "Before, during and after care", "The first minutes of an emergency"),
]
with pdf.table(col_widths=[40, 64, 74], headings_style=heads, line_height=6.0, first_row_as_headings=True,
               cell_fill_color=MINT, cell_fill_mode="ROWS", borders_layout="HORIZONTAL_LINES",
               text_align="LEFT") as tb:
    r = tb.row()
    for h in ("", "NHIA", "VITALIS"):
        r.cell(h)
    for row in rows:
        r = tb.row()
        for c in row:
            r.cell(t(c))
pdf.ln(4)

# together
pdf.set_fill_color(*MINT)
y = pdf.get_y()
pdf.rect(16, y, W, 55, style="F")
pdf.set_fill_color(*GREEN)
pdf.rect(16, y, 1.6, 55, style="F")
pdf.set_xy(22, y + 4)
pdf.set_font("helvetica", "B", 12)
pdf.cell(0, 6, "Working together", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("helvetica", "", 10.5)
together = [
    "**Today:** a patient adds her NHIA number to her VITALIS ID; reception sees it the moment she arrives, so "
    "coverage can be checked without another form.",
    "**Today:** hospitals show **Accepts NHIA** and **Free maternal care**; an insured patient sees those first, "
    "but only among hospitals that can treat her. Saved on the phone, so it works with no signal.",
    "**Today:** no smartphone or data needed: people dial a USSD code from any phone and the hospital answers by "
    "SMS, reaching the same families the Vulnerable Group Fund is for.",
    "**Next (planned):** referral and arrival records that can support claims and help the NHIA see where care is "
    "needed most.",
]
for it in together:
    pdf.set_x(22)
    pdf.multi_cell(W - 12, 5.3, t(it), markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.7)

# footer
pdf.set_y(-21)
pdf.set_font("helvetica", "B", 10.5)
pdf.set_text_color(*GREEN)
pdf.cell(0, 6, t("Insurance makes care affordable. Coordination makes it reachable."), new_x="LMARGIN", new_y="NEXT")
pdf.set_font("helvetica", "", 7.8)
pdf.set_text_color(*MUTED)
pdf.multi_cell(W, 3.8, t(
    "VITALIS is an independent ITDC 2026 hackathon project and is not affiliated with or endorsed by the NHIA. Demo: "
    "vitalis.olamide.cloud (synthetic data). NHIA facts: National Health Insurance Authority Act, 2022 (signed May "
    "2022; repealed the NHIS Act Cap N42, 2004)."), align="L", new_x="LMARGIN", new_y="NEXT")
pdf.output(str(OUT))
print(OUT)
