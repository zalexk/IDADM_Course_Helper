from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pandas as pd
from io import BytesIO
from datetime import datetime

def generate_study_plan_docx(overall_study_plan_df: pd.DataFrame, major_2_name: str):
    doc = Document()
    
    # Title
    title = doc.add_heading('IDADM Study Plan', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Second Major Info
    p = doc.add_paragraph()
    p.add_run(f'Second Major: ').bold = True
    p.add_run(major_2_name)
    
    # Generation Date
    p = doc.add_paragraph()
    p.add_run(f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

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
        doc.add_heading(f'Year {year}', level=1)
        
        periods = [f"Year {year} Sem 1", f"Year {year} Sem 2"]
        if year < 4:
            periods.extend([f"Year {year} Summer (CUHK)", f"Year {year} Summer (CUHKSZ)"])

        year_total_credits = 0
        
        for period in periods:
            campus = study_campus.get(period, "N/A")
            period_df = overall_study_plan_df[overall_study_plan_df["Study Period"] == period]
            
            if not period_df.empty:
                # Semester Heading
                p = doc.add_paragraph()
                title = f"{period} ({campus})" if campus not in period else period
                run = p.add_run(title)
                run.bold = True
                run.font.size = Pt(12)
                
                # Table
                table = doc.add_table(rows=1, cols=2)
                table.style = 'Table Grid'
                table.autofit = False
                
                # Set column widths: Course (5 inches), Credits (1 inch)
                table.columns[0].width = Inches(5.0)
                table.columns[1].width = Inches(1.0)
                
                # Header row
                hdr_cells = table.rows[0].cells
                hdr_cells[0].text = 'Course'
                hdr_cells[0].width = Inches(5.0)
                hdr_cells[1].text = 'Credits'
                hdr_cells[1].width = Inches(1.0)
                # Set bold for header
                for cell in hdr_cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.bold = True

                # Data rows
                display_df = period_df.filter([campus, "Credits"])
                for _, data_row in display_df.iterrows():
                    row_cells = table.add_row().cells
                    row_cells[0].text = str(data_row[campus])
                    row_cells[0].width = Inches(5.0)
                    row_cells[1].text = str(data_row["Credits"])
                    row_cells[1].width = Inches(1.0)
                    row_cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

                # Subtotal
                period_credits = period_df["Credits"].sum()
                year_total_credits += period_credits
                p = doc.add_paragraph()
                p.add_run(f'Subtotal Credits: {period_credits}').italic = True
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                doc.add_paragraph() # Spacer

        # Year Total
        p = doc.add_paragraph()
        run = p.add_run(f'Year {year} Total Credits: {year_total_credits}')
        run.bold = True
        run.font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        
        if year < 4:
            doc.add_page_break()

    # Save to buffer
    target_stream = BytesIO()
    doc.save(target_stream)
    target_stream.seek(0)
    return target_stream
