"""PDF export: built-in latin-1 fonts must never crash on typographic text.

Regression: course titles in course_list.csv use an en dash (e.g. "ELTU2024
English for Engineering Students I – Extensive Reading about Contemporary
Issues"); fpdf2's core Helvetica cannot encode it, which used to fail the
whole export with FPDFUnicodeEncodingException.
"""

import pandas as pd
import pypdfium2 as pdfium

from src.pdf_generator import _pdf_safe, generate_study_plan_pdf


def _pdf_text(pdf_bytes : bytes) -> str:
    """Extract the text of every page (pdfium is already a project dependency:
    the import pipeline renders transcript pages with it)."""
    document = pdfium.PdfDocument(pdf_bytes)
    try:
        return "".join(
            document[index].get_textpage().get_text_range()
            for index in range(len(document))
        )
    finally:
        document.close()


class TestPdfSafeText:
    def test_en_dash_maps_to_hyphen(self):
        assert _pdf_safe("Students I \u2013 Extensive Reading") == "Students I - Extensive Reading"

    def test_curly_quotes_em_dash_and_ellipsis_map(self):
        assert _pdf_safe("\u201cA\u201d \u2014 B\u2026") == '"A" - B...'

    def test_unmapped_char_falls_back_to_question_mark(self):
        assert _pdf_safe("\u6e2c\u8a66") == "??"


class TestGeneratePdf:
    def test_en_dash_title_export_succeeds(self):
        df = pd.DataFrame([
            {
                "Course": "ELTU2024 English for Engineering Students I \u2013 Extensive Reading about Contemporary Issues",
                "Credits": 3,
                "Study Period": "Year 1 Sem 1",
            },
        ])
        out = generate_study_plan_pdf(df, "Information Engineering")
        assert out.startswith(b"%PDF")

    def test_export_handles_empty_plan(self):
        df = pd.DataFrame(columns=["Course", "Credits", "Study Period"])
        out = generate_study_plan_pdf(df, "Information Engineering")
        assert out.startswith(b"%PDF")

    def test_blank_period_row_exports_selected_section(self):
        # A course ticked as Selected but not yet scheduled must not vanish
        # from the export: it gets a closing section of its own (titles still
        # go through _pdf_safe, hence the en dash).
        df = pd.DataFrame([
            {"Course": "CSCI1120 Introduction to Computing", "Credits": 3,
             "Study Period": "Year 1 Sem 1"},
            {"Course": "MATH1010 Calculus \u2013 Series", "Credits": 3,
             "Study Period": None},
        ])
        out = generate_study_plan_pdf(df, "Information Engineering")
        assert out.startswith(b"%PDF")
        text = _pdf_text(out)
        assert "Selected Courses (No Study Period)" in text
        assert "MATH1010 Calculus - Series" in text
        assert "Total Selected Credits: 3" in text

    def test_no_selected_section_when_all_courses_scheduled(self):
        df = pd.DataFrame([
            {"Course": "CSCI1120 Introduction to Computing", "Credits": 3,
             "Study Period": "Year 1 Sem 1"},
        ])
        text = _pdf_text(generate_study_plan_pdf(df, "Information Engineering"))
        assert "Selected Courses" not in text
