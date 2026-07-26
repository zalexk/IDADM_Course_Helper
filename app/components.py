
from typing import Any, Literal

import pandas as pd
import streamlit as st
from streamlit.elements.lib.column_types import SelectboxOptionValue

from app.constant import STUDY_CAMPUS


study_period_col_config: dict[str, Any] = {
    "Study Period": st.column_config.SelectboxColumn(
        "Study Period",
        options=list[SelectboxOptionValue](STUDY_CAMPUS.keys()),
    )
}


def table_editor(
    course_table: pd.DataFrame,
    element_key: str,
    func, 
    col_config: dict[str, Any] | None = None,
    num_of_rows: Literal["fixed", "dynamic"] = "fixed",
    disabled_col: list[str] = ["CUHK", "CUHKSZ", "Credits"]
) -> pd.DataFrame:
    
    if col_config is None:
        col_config = study_period_col_config

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
