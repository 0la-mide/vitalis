"""Printable teleprompter: pitch/TELEPROMPTER.md -> pitch/VITALIS-teleprompter.pdf (large type, A4).

Run: cd backend && uv run python ../pitch/teleprompter/build.py
"""
import re
from pathlib import Path

from fpdf import FPDF

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "TELEPROMPTER.md"
OUT = HERE.parent / "VITALIS-teleprompter.pdf"
GREEN, TEAL, INK, MUTED, MINT = (15, 92, 74), (19, 78, 94), (20, 32, 28), (110, 120, 116), (238, 246, 243)


def t(s: str) -> str:
    for a, b in {"—": "-", "–": "-", "’": "'", "“": '"', "”": '"', "·": "-", "…": "...", "→": "->"}.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


class Doc(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "", 9)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"VITALIS teleprompter  -  page {self.page_no()}", align="C")


pdf = Doc(format="A4")
pdf.set_margins(20, 16, 20)
pdf.set_auto_page_break(True, margin=18)
pdf.add_page()
W = pdf.w - 40

lines = SRC.read_text().splitlines()
in_notes = False
for raw in lines:
    line = raw.rstrip()
    if not line or line == "---":
        pdf.ln(2.5)
        continue
    if line.startswith("# "):
        pdf.set_font("helvetica", "B", 24)
        pdf.set_text_color(*GREEN)
        pdf.multi_cell(W, 11, t(line[2:]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        continue
    if line.startswith("### "):
        in_notes = True
        if pdf.get_y() > pdf.h - 70:
            pdf.add_page()
        pdf.ln(3)
        pdf.set_font("helvetica", "B", 15)
        pdf.set_text_color(*INK)
        pdf.multi_cell(W, 8, t(line[4:]), new_x="LMARGIN", new_y="NEXT")
        continue
    if line.startswith("## "):
        head = line[3:]
        if pdf.get_y() > pdf.h - 92:  # keep a section and its lines on one page
            pdf.add_page()
        pdf.ln(3)
        m = re.match(r"(\d:\d\d) · \*\((.*)\)\*", head)
        y = pdf.get_y()
        pdf.set_fill_color(*MINT)
        pdf.rect(20, y, W, 11, style="F")
        pdf.set_xy(24, y + 1.5)
        if m:
            pdf.set_font("helvetica", "B", 17)
            pdf.set_text_color(*GREEN)
            pdf.cell(20, 8, m.group(1))
            pdf.set_font("helvetica", "I", 12)
            pdf.set_text_color(*TEAL)
            pdf.cell(W - 26, 8, t(m.group(2)))
        else:
            pdf.set_font("helvetica", "B", 15)
            pdf.set_text_color(*GREEN)
            pdf.cell(W - 8, 8, t(head))
        pdf.set_xy(20, y + 14)
        continue
    if line.startswith("- "):  # delivery notes
        pdf.set_font("helvetica", "", 12)
        pdf.set_text_color(*INK)
        pdf.cell(6, 6.5, "-")
        pdf.multi_cell(W - 6, 6.5, t(line[2:]), markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")
        continue
    cue = re.fullmatch(r"\*\((.*)\)\*", line)
    if cue:
        pdf.set_font("helvetica", "I", 13)
        pdf.set_text_color(*TEAL)
        pdf.multi_cell(W, 7, t(f"[ {cue.group(1)} ]"), align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        continue
    # the words to say: big, with pauses and bold kept
    text = line.replace("`", "")
    small = in_notes or text.startswith("Play ") or text.startswith("Timecodes") or text.startswith("`/`") \
        or "= short breath" in raw
    if small:
        pdf.set_font("helvetica", "", 11.5)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(W, 6, t(text), markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")
        continue
    text = re.sub(r"\s*//\s*$", "  //", text)
    pdf.set_font("helvetica", "", 21)
    pdf.set_text_color(*INK)
    pdf.multi_cell(W, 10.5, t(text), markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")

pdf.output(str(OUT))
print(OUT, pdf.page_no(), "pages")
