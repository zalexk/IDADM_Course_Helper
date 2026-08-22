"""PDF export for the overall study plan.

Mirrors the production layout: title + 2nd major, grouped by year (one page per
year), each semester/summer shown as a Course/Credits table with a subtotal,
and a year-total at the bottom. Adapted to the refactored unified course table
(`Course Credits Study Period`) instead of the old CUHK/CUHKSZ split columns.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from fpdf import FPDF
from fpdf.fonts import FontFace
from fpdf.enums import XPos, YPos

import pandas as pd

from app.constant import STUDY_CAMPUS


def _format_now(user_tz : str | None) -> str:
    """Return "YYYY-MM-DD HH:MM" in the user's tz, UTC if unknown/invalid.

    Avoids leaking the server clock (UTC on Streamlit Cloud) into the export
    footer when the browser reports a different timezone via st.context.
    """
    try:
        tz = ZoneInfo(user_tz) if user_tz else ZoneInfo("UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M")


class StudyPlanPDF(FPDF):
    def __init__(self, *, user_tz : str | None = None, **kwargs):
        super().__init__(**kwargs)
        # Captured once so every page footer shows the same timestamp.
        self._generated_on = _format_now(user_tz)

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "IDADM Study Plan", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} - Generated on {self._generated_on}", align="C")


def generate_study_plan_pdf(study_plan_df : pd.DataFrame, major_2_name : str, *, user_tz : str | None = None) -> bytes:
    """Generate a PDF from the unified study-plan DataFrame.

    Expected columns: Course, Credits, Study Period.
    `user_tz` is an IANA timezone name (e.g. "Asia/Hong_Kong") forwarded from
    `st.context.timezone`; UTC is used when the caller doesn't supply one.
    """
    pdf = StudyPlanPDF(user_tz=user_tz)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Second Major: {major_2_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    for year in range(1, 5):
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, f"Year {year}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(2)

        periods = [f"Year {year} Sem 1", f"Year {year} Sem 2"]
        if year < 4:
            periods.extend([f"Year {year} Summer (CUHK)", f"Year {year} Summer (CUHKSZ)"])

        year_total_credits = 0

        for period in periods:
            period_df = study_plan_df[study_plan_df["Study Period"] == period]

            if not period_df.empty:
                pdf.set_font("Helvetica", "B", 11)
                # Use simple period name; campus is already embedded in summer labels
                title = period if STUDY_CAMPUS.get(period, "") in period else f"{period} ({STUDY_CAMPUS.get(period, 'N/A')})"
                pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

                pdf.set_font("Helvetica", "", 10)

                display_df = period_df.filter(["Course", "Credits"])

                with pdf.table(
                    borders_layout="SINGLE_TOP_LINE",
                    cell_fill_color=255,
                    cell_fill_mode="ROWS",
                    line_height=6,
                    text_align=("LEFT", "CENTER"),
                    width=160,
                    col_widths=(85, 15),
                ) as table:
                    row = table.row()
                    row.cell("Course", style=FontFace(emphasis="BOLD"))
                    row.cell("Credits", style=FontFace(emphasis="BOLD"))

                    for _, data_row in display_df.iterrows():
                        row = table.row()
                        row.cell(str(data_row["Course"]))
                        row.cell(str(data_row["Credits"]))

                period_credits = int(period_df["Credits"].sum())
                year_total_credits += period_credits
                pdf.set_font("Helvetica", "I", 10)
                pdf.cell(0, 8, f"Subtotal Credits: {period_credits}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
                pdf.ln(2)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 10, f"Year {year} Total Credits: {year_total_credits}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        pdf.ln(5)

        if year < 4:
            pdf.add_page()

    return bytes(pdf.output())
