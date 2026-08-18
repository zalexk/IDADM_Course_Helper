"""2nd Major tab.

Catalogue-backed tables: Required Courses, Research Component, and Elective
Courses. All course lists and equivalence conversion use the user's selected
2nd major.
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
    st.info("Only the grade of the Research Component counts in the Major GPA for the Second Major")

    for category in ("Required Courses", "Research Component", "Elective Courses"):
        st.subheader(category)

        # "Elective Courses" in the UI maps to "2nd Major Elective Courses" in the data.
        data_key = "2nd Major Elective Courses" if category == "Elective Courses" else category
        course_list = get_course_list(context, major_2)[data_key]

        _catalog_table(
            context, major_2, course_list,
            element_key=f"major2-{data_key.lower().replace(' ', '-')}",
        )
