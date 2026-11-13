"""DEMO_LOGINS.pdf: every seeded demo account on one printable sheet (synthetic data, never committed)."""

from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

PRIMARY = (15, 92, 74)
MUTED = (90, 100, 98)
ROLE_ORDER = ["facility_admin", "receptionist", "nurse", "doctor", "lab", "radiology"]
ROLE_LABEL = {"pending nurse": "Nurse (pending)", "facility_admin": "Hospital admin", "receptionist": "Reception", "nurse": "Nurse",
              "doctor": "Doctor", "lab": "Lab", "radiology": "Radiology"}


def _t(s: str) -> str:
    """Core PDF fonts are Latin-1 only."""
    return (s.replace("—", "-").replace("–", "-").replace("·", "-").replace("’", "'")
            .encode("latin-1", "replace").decode("latin-1"))


class _Doc(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 9)
        self.set_text_color(*MUTED)
        self.cell(0, 6, _t("VITALIS - demo logins - synthetic data only"), align="R")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")


def _heading(pdf: FPDF, text: str) -> None:
    pdf.ln(3)
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 8, _t(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def _table(pdf: FPDF, head: list[str], rows: list[list[str]], widths: list[int]) -> None:
    pdf.set_font("helvetica", "", 9.5)
    heads = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=PRIMARY)
    with pdf.table(col_widths=widths, headings_style=heads, line_height=6.5, first_row_as_headings=True,
                   cell_fill_color=(240, 247, 244), cell_fill_mode="ROWS", borders_layout="HORIZONTAL_LINES") as table:
        r = table.row()
        for h in head:
            r.cell(_t(h))
        for row in rows:
            r = table.row()
            for c in row:
                r.cell(_t(c))


def write_logins_pdf(out: Path, *, password: str, base_url: str, logins: list[tuple[str, str, str]],
                     patients: list[tuple[str, str, str]], facility_roles: list[tuple[str, str]]) -> Path:
    """logins: (who, email, status); patients: (name, vitalis_id, recovery_code); facility_roles: (name, demo role)."""
    pdf = _Doc(format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.set_margins(14, 12, 14)
    pdf.add_page()

    pdf.set_font("helvetica", "B", 20)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 10, "VITALIS demo logins", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 5, _t(f"Sign in at {base_url}/auth/login. Every account uses the same password. "
                            "All people, hospitals and records are synthetic. Do not share outside the team "
                            "and judges."), align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_fill_color(240, 247, 244)
    pdf.set_draw_color(*PRIMARY)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 11, _t(f"  Password for every account:   {password}"), border=1, fill=True,
             new_x="LMARGIN", new_y="NEXT")

    # Accounts not tied to a hospital, then each hospital as one row of roles.
    general, by_facility = [], {}
    for who, email, status in logins:
        if " - " in who:
            fac, role = who.rsplit(" - ", 1)
            by_facility.setdefault(fac, {})[role] = (email, status)
        else:
            general.append([who, email, status])

    _heading(pdf, "Network and frontline accounts")
    _table(pdf, ["Who", "Email", "Status"], general, [50, 90, 42])

    _heading(pdf, "Hospital staff")
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 4.5, _t("Each hospital has the same six roles. Emails follow role.hospital@vitalis.demo."),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)
    rows = []
    for fac in sorted(by_facility):
        for role in ROLE_ORDER + sorted(set(by_facility[fac]) - set(ROLE_ORDER)):
            if role in by_facility[fac]:
                email, status = by_facility[fac][role]
                rows.append([fac.replace(" (Demo)", ""), ROLE_LABEL.get(role, role), email,
                             "" if status == "approved" else status])
    # Pending examples (verification demo) are sorted with their hospital.
    _table(pdf, ["Hospital", "Role", "Email", "Note"], rows, [58, 28, 76, 20])

    _heading(pdf, "Demo patients (My health record: tap the name, or restore with ID + code)")
    _table(pdf, ["Patient", "VITALIS ID", "Recovery code"], [list(p) for p in patients], [70, 50, 62])
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 4.5, _t("A recovery code works once: restoring gives the phone a new code. Reseed "
                              "(make demo-reset, or deploy.sh --reset-demo) to get fresh codes and a new PDF."),
                   new_x="LMARGIN", new_y="NEXT")

    if facility_roles:
        _heading(pdf, "Who does what in the demo story")
        pdf.set_font("helvetica", "", 9.5)
        pdf.set_text_color(0, 0, 0)
        for name, role in facility_roles:
            pdf.multi_cell(0, 5, _t(f"- {name}: {role}"), new_x="LMARGIN", new_y="NEXT")

    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    return out
