from fpdf import FPDF
from fpdf.fonts import FontFace
from fpdf.enums import XPos, YPos
import pandas as pd
from datetime import datetime

class StudyPlanPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        # Use new_x and new_y instead of ln=True (deprecated)
        self.cell(0, 10, "IDADM Study Plan", border=False, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")

def generate_study_plan_pdf(overall_study_plan_df: pd.DataFrame, major_2_name: str):
    pdf = StudyPlanPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Second Major: {major_2_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    study_campus = {
        "Year 1 Sem 1": "CUHK",
        "Year 1 Sem 2": "CUHKSZ",
        "Year 1 Summer (CUHK)": "CUHK",
        "Year 1 Summer (CUHKSZ)": "CUHKSZ",
        "Year 2 Sem 1": "CUHKSZ",
        "Year 2 Sem 2": "CUHK",
        "Year 2 Summer (CUHK)": "CUHK",
        "Year 2 Summer (CUHKSZ)": "CUHKSZ",
        "Year 3 Sem 1": "CUHK",
        "Year 3 Sem 2": "CUHKSZ",
        "Year 3 Summer (CUHK)": "CUHK",
        "Year 3 Summer (CUHKSZ)": "CUHKSZ",
        "Year 4 Sem 1": "CUHKSZ",
        "Year 4 Sem 2": "CUHK"
    }

    # Group by Year
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
            campus = study_campus.get(period, "N/A")
            period_df = overall_study_plan_df[overall_study_plan_df["Study Period"] == period]
            
            if not period_df.empty:
                pdf.set_font("Helvetica", "B", 11)
                
                # Use simple period name for title to avoid redundancy like "Year 1 Summer (CUHK) (CUHK)"
                title = period
                pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                # Reset font to regular for the table
                pdf.set_font("Helvetica", "", 10)

                # Filter columns to show based on campus
                display_df = period_df.filter([campus, "Credits"])
                display_df.columns = ["Course", "Credits"]
                
                # Add table
                with pdf.table(
                    borders_layout="SINGLE_TOP_LINE",
                    cell_fill_color=255,
                    cell_fill_mode="ROWS",
                    line_height=6,
                    text_align=("LEFT", "CENTER"),
                    width=160, # Increase total table width
                    col_widths=(85, 15) # 85% for Course, 15% for Credits
                ) as table:
                    # Header
                    row = table.row()
                    row.cell("Course", style=FontFace(emphasis="BOLD"))
                    row.cell("Credits", style=FontFace(emphasis="BOLD"))
                    
                    # Data
                    for _, data_row in display_df.iterrows():
                        row = table.row()
                        row.cell(str(data_row["Course"]))
                        row.cell(str(data_row["Credits"]))
                
                period_credits = period_df["Credits"].sum()
                year_total_credits += period_credits
                pdf.set_font("Helvetica", "I", 10)
                pdf.cell(0, 8, f"Subtotal Credits: {period_credits}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
                pdf.ln(2)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 10, f"Year {year} Total Credits: {year_total_credits}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        pdf.ln(5)
        
        # Add a page break after each year except the last one if it doesn't fit
        if year < 4:
            pdf.add_page()

    # Streamlit's st.download_button expects 'bytes', but fpdf2 returns 'bytearray'
    return bytes(pdf.output())
