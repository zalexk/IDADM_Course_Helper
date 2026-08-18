import streamlit as st
from src.data_retrieval import CourseDataContext, get_course_list, show_course_info, _course_key
import pandas as pd
from app.components import table_editor, study_period_col_config
from src.storage import (
    data_on_change,
    pe_on_change,
    college_ge_on_change,
    four_area_on_change,
    fetch_data,
)


def _user_input_section(
    header : str,
    element_key : str,
    on_change_func,
    table_name : str,
    default_rows : int,
    default_credits : int,
    dynamic : bool,
) -> None:
    """Build a user-input course table (no catalogue; identity = typed CUHK code).

    Recall fills the table from its own DB table so sections never collide with
    each other or with catalogue rows. `dynamic` controls num_rows.
    """
    st.header(header)

    user_id = st.session_state.get("user_id")
    saved = fetch_data(user_id, table_name) if user_id else []

    saved_count = len(saved)
    row_count = max(saved_count, default_rows)
    if saved:
        cuhk   = [row["course_id"]   for row in saved] + [""] * (row_count - saved_count)
        period = [row["study_period"] for row in saved] + [""] * (row_count - saved_count)
    else:
        cuhk   = [""] * row_count
        period = [""] * row_count
    n = row_count

    course_table = pd.DataFrame(
        {
            "CUHK": cuhk,
            "CUHKSZ": [""] * n,
            "Credits": [default_credits] * n,
            "Study Period": period,
        },
    )

    table_editor(
        course_table.filter(["CUHK", "CUHKSZ", "Credits", "Study Period"]),
        element_key=element_key,
        col_config=study_period_col_config,
        disabled_col=[],
        func=on_change_func,
        num_of_rows="dynamic" if dynamic else "fixed",
    )


def ui(context : CourseDataContext):
    course_list = get_course_list(context, "University Core")["Required Courses"]

    course_table = pd.DataFrame(
        {
            "CUHK" : show_course_info(context, "University Core", course_list, "hk"),
            "CUHKSZ" : show_course_info(context, "University Core", course_list, "sz"),
            "Credits" : show_course_info(context, "University Core", course_list, "hk", "credits"),
            "Study Period" : show_course_info(context, "University Core", course_list, "hk", "study_period")
        },
        index = pd.Index([_course_key(context, "University Core", c) for c in course_list])
    )
    table_editor(
        course_table.filter(["CUHK", "CUHKSZ", "Credits", "Study Period"]),
        element_key = "ucore-compulsory",
        col_config = study_period_col_config,
        disabled_col = [],
        func = data_on_change
    )

    _user_input_section(
        "Physical Education", "ucore-pe", pe_on_change,
        table_name="pe", default_rows=1, default_credits=1, dynamic=False,
    )
    _user_input_section(
        "College GE", "ucore-college-ge", college_ge_on_change,
        table_name="college_ge", default_rows=1, default_credits=3, dynamic=True,
    )
    _user_input_section(
        "Four Area of GE", "ucore-four-area-ge", four_area_on_change,
        table_name="four_area_ge", default_rows=1, default_credits=3, dynamic=True,
    )