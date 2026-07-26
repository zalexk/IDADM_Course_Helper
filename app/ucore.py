import streamlit as st
from src.data_retrieval import CourseDataContext, get_course_list, show_course_info
import pandas as pd
from app.components import table_editor, study_period_col_config
from src.storage import data_on_change

def ui(context : CourseDataContext):
    course_list = get_course_list(context, "University Core")["Required Courses"]
    
    course_table = pd.DataFrame(
        {
            "CUHK" : show_course_info(context, "University Core", course_list, "hk"), 
            "CUHKSZ" : show_course_info(context, "University Core", course_list, "sz"), 
            "Credits" : show_course_info(context, "University Core", course_list, "hk", "credits"),
            "Study Period" : [" " for i in range(len(course_list))]
        }
    )
    
    study_period_col_config["Credits"] = st.column_config.NumberColumn(
        "Credits",
        width = "small",
        required = True,
        min_value = 0,
        max_value = 10,
        step = "int" # type: ignore[return-value]
    )
    
    table_editor(
        course_table.filter(["CUHK", "CUHKSZ", "Credits", "Study Period"]),
        element_key = "ucore-compulsory",
        col_config = study_period_col_config,
        disabled_col = [],
        func = data_on_change
    )
    
    st.header("Physical Education")

    st.write("Hello")