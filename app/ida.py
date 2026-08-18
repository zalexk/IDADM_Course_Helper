"""Interdisciplinary Data Analytics (1st Major) tab.

Catalogue-backed tables: Faculty Package, Required Courses, COOP, and
Elective Courses (Group A / B). Equivalence conversion uses the IDA major;
Group A/B course lists come from the user's selected 2nd major (matches the
pre-refactor production behaviour).
"""

import streamlit as st
import pandas as pd

from src.data_retrieval import (
    CourseDataContext,
    get_course_list,
    show_course_info,
    _course_key,
)
from app.components import table_editor, study_period_col_config
from src.storage import data_on_change

_IDA = "Interdisciplinary Data Analytics"


def _catalog_table(
    context : CourseDataContext,
    major : str,
    course_list : list[str],
    element_key : str,
) -> None:
    """Build a catalogue-backed course table with canonical-key index."""
    course_table = pd.DataFrame(
        {
            "CUHK": show_course_info(context, major, course_list, "hk"),
            "CUHKSZ": show_course_info(context, major, course_list, "sz"),
            "Credits": show_course_info(context, major, course_list, "hk", "credits"),
            "Study Period": show_course_info(context, major, course_list, "hk", "study_period"),
        },
        index=pd.Index([_course_key(context, major, c) for c in course_list]),
    )

    table_editor(
        course_table.filter(["CUHK", "CUHKSZ", "Credits", "Study Period"]),
        element_key=element_key,
        col_config=study_period_col_config,
        disabled_col=[],
        func=data_on_change,
    )


def ui(context : CourseDataContext, major_2 : str) -> None:
    # --- Fixed catalogue sections ---
    for category in ("Faculty Package", "Required Courses", "COOP"):
        st.subheader(category)
        course_list = get_course_list(context, _IDA)[category]
        _catalog_table(
            context, _IDA, course_list,
            element_key=f"ida-{category.lower().replace(' ', '-')}",
        )

    # --- Elective Courses (Group A / B) ---
    st.subheader("Elective Courses")
    st.info("""Requirement: 6-15 units from Group A + 12-21 units from Group B

At least 12 units level 3000+ (including 6 units level 4000+)
""")

    for group in ("A", "B"):
        st.markdown(f"**Group {group}**")
        # Course list comes from the 2nd major, but equivalence uses IDA.
        course_list = get_course_list(context, major_2)["1st Major Elective Courses"][group]
        _catalog_table(
            context, _IDA, course_list,
            element_key=f"ida-elective-{group.lower()}",
        )
