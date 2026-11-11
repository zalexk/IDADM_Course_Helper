
from typing import Any, Literal

import pandas as pd
import streamlit as st
from streamlit.elements.lib.column_types import SelectboxOptionValue

from app.constant import STUDY_CAMPUS


study_period_col_config: dict[str, Any] = {
    "Credits": st.column_config.NumberColumn(
        "Credits",
        width="small",
        required=True,
        min_value=0,
        max_value=10,
        step="int", # type: ignore[return-value]
    ),
    "Selected": st.column_config.CheckboxColumn(
        "Selected",
        width="small",
        help=(
            "Tick to plan this course — you can pick a study period later. "
            "Un-ticking clears its Study Period."
        ),
    ),
    "Study Period": st.column_config.SelectboxColumn(
        "Study Period",
        options=list[SelectboxOptionValue](STUDY_CAMPUS.keys()),
    ),
}


# Catalogue rows carry the official course codes, titles and credit units, so
# they must not be edited. Free-entry tables (PE, College GE, Four Area of GE,
# Other Courses) pass an explicit empty list: there the student types the code
# and credits of a course that has no catalogue row.
CATALOGUE_LOCKED_COLUMNS : list[str] = ["CUHK", "CUHKSZ", "Credits"]


def table_editor(
    course_table: pd.DataFrame,
    element_key: str,
    func, 
    col_config: dict[str, Any] | None = None,
    num_of_rows: Literal["fixed", "dynamic"] = "fixed",
    disabled_col: list[str] | None = None
) -> pd.DataFrame:
    """Render a course table; catalogue columns are read-only by default."""
    if col_config is None:
        col_config = study_period_col_config
    if disabled_col is None:
        disabled_col = list(CATALOGUE_LOCKED_COLUMNS)

    df = st.data_editor(
        course_table,
        hide_index = True,
        height = "content",
        num_rows = num_of_rows,
        column_config = col_config,
        disabled = disabled_col,
        key = element_key,
        on_change = func,
        args = (element_key, course_table) # Convert to tuple
    )
    return df
