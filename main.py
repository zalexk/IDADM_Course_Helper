import streamlit as st
import data_retrieval as data
import pandas as pd

# ---------------- Initialization ----------------
if "study_planner" not in st.session_state:
    st.session_state.study_planner = [{}]
    # Store in session state
    
if "study_plan" not in st.session_state:
    st.session_state.study_plan = [pd.DataFrame(columns=["CUHK", "CUHKSZ", "Credits", "Study Period"])]
    
if "planner_update_count" not in st.session_state:
    st.session_state.planner_update_count = 0 

# ---------------- Config ----------------
study_period_col_config = {
                        "Study Period" : st.column_config.SelectboxColumn(
                            "Study Period",
                            options = [
                                "Year 1 Sem 1",
                                "Year 1 Sem 2",
                                "Year 2 Sem 1",
                                "Year 2 Sem 2",
                                "Year 3 Sem 1",
                                "Year 3 Sem 2",
                                "Year 4 Sem 1",
                                "Year 4 Sem 2"
                            ]
                        )
                    }

# ---------------- Functions ----------------
def select_major(major_list : tuple) -> str | None:
    major = st.selectbox(
        "2nd Major",
        major_list, 
        index = None,
        placeholder = "Select your second major"
    )
    
    return major

def update_study_plan():
    """
    Concatenates all dataframes currently stored in study_planner[0].
    """
    if st.session_state.study_planner[0]:
        st.session_state.study_plan[0] = pd.concat(
            [df for df in st.session_state.study_planner[0].values()],
            ignore_index=True
        )

def ucore_info():
    course_table = pd.DataFrame(columns=["CUHK", "CUHKSZ", "Credits", "Study Period"])
    # Create empty DataFrame for user input
    
    study_period_col_config["Credits"] = st.column_config.NumberColumn(
        "Credits",
        width = "small",
        required = True,
        min_value = 0,
        max_value = 10,
        step = "int"
    )
    
    st.session_state.study_planner[0]["University Core"] = st.data_editor(
        course_table,
        num_rows = "dynamic",
        column_config = study_period_col_config,
        key = "ucore_data" # Add unique key
    )


def IDA_info(major_2 : str) -> None:
    for i in ("Faculty Package", "Required Courses", "COOP"):
        st.subheader(i)
        
        course_list = data.get_course_list("Interdisciplinary Data Analytics")[i]
        
        course_table = pd.DataFrame(
            {
                "CUHK": data.show_course_info(
                        "Interdisciplinary Data Analytics",
                        course_list,
                        "hk"
                    ),
                
                "CUHKSZ": data.show_course_info(
                    "Interdisciplinary Data Analytics",
                    course_list,
                    "sz"
                ),
                "Credits" : data.show_course_info(
                    "Interdisciplinary Data Analytics",
                    course_list,
                    "hk", # Campus can be ignored
                    "credits"
                ),
                "Study Period" : [" " for _ in range(len(course_list))]
                # Generate empty data with same row with other columns
            }
        )
        
        st.session_state.study_planner[0][f"IDA - {i}"] = st.data_editor(course_table,
                    column_order = None,
                    hide_index = True,
                    height = "content",
                    column_config = study_period_col_config,
                    disabled = ["CUHK", "CUHKSZ", "Credits"],
                    key = f"IDA_{i}_data"
            )
        
    
    st.subheader("Elective Courses")
    
    st.info("""Requirement: 6-15 units from Group A + 12-21 units from Group B
            
At least 12 units level 3000+ (incl 6 units level 4000+)
""")

    for i in ("A", "B"):
        st.markdown(f"**Group {i}**")
        
        course_list = data.get_course_list(major_2)["1st Major Elective Courses"][i]
        
        elective_table = pd.DataFrame(
            {
                "CUHK": data.show_course_info(
                        "Interdisciplinary Data Analytics",
                        course_list,
                        "hk"
                    ),
                
                "CUHKSZ": data.show_course_info(
                    "Interdisciplinary Data Analytics",
                    course_list,
                    "sz"
                ),
                "Credits": data.show_course_info(
                    "Interdisciplinary Data Analytics",
                    course_list,
                    "sz",
                    "credits"
                ),
                "Study Period" : [" " for _ in range(len(course_list))]
            }
        )
        
        st.session_state.study_planner[0][f"IDA - {i}"] = st.data_editor(elective_table,
                    column_order = None,
                    hide_index = True,
                    height = "content",
                    column_config = study_period_col_config,
                    disabled = ["CUHK", "CUHKSZ", "Credits"],
                    key = f"IDA_Elective_{i}"
                    )
        

def major_2_info(major_2 : str) -> None:
    st.info("Only the grade of the Research Component counts in the Major GPA for the Second Major")
    
    for i in ("Required Courses", "Research Component", "Elective Courses"):
        st.subheader(i)
        
        if i == "Elective Courses":
            i = "2nd Major Elective Courses"
            
        course_list = data.get_course_list(major_2)[i]
        
        course_table = pd.DataFrame(
            {
                "CUHK": data.show_course_info(
                        major_2,
                        course_list,
                        "hk"
                    ),
                
                "CUHKSZ": data.show_course_info(
                    major_2,
                    course_list,
                    "sz"
                    ),
                "Credits": data.show_course_info(
                    major_2,
                    course_list,
                    "sz",
                    "credits"
                    ),
                "Study Period" : [" " for _ in range(len(course_list))]
            }
        )
        
        st.session_state.study_planner[0][f"2nd Major - {i}"] = st.data_editor(course_table,
                    column_order = None,
                    hide_index = True,
                    height = "content",
                    column_config = study_period_col_config,
                    disabled = ["CUHK", "CUHKSZ", "Credits"],
                    key = f"major_2_{i}"
                    )
            
def show_planner(year : int):
    study_campus = {
        "Year 1 Sem 1": "CUHK",
        "Year 1 Sem 2": "CUHKSZ",
        "Year 2 Sem 1": "CUHKSZ",
        "Year 2 Sem 2": "CUHK",
        "Year 3 Sem 1": "CUHK",
        "Year 3 Sem 2": "CUHKSZ",
        "Year 4 Sem 1": "CUHKSZ",
        "Year 4 Sem 2": "CUHK"
    }
    study_plan = st.session_state.study_plan[0]
    
  
    sem1, sem2 = st.columns(2)
    
    with sem1:
        st.subheader(f"Sem 1 ({study_campus[f"Year {year} Sem 1"]})")
        
        filtered_study_plan = study_plan[study_plan["Study Period"] == f"Year {year} Sem 1"].filter([study_campus[f"Year {year} Sem 1"], "Credits"])
        
        
        st.dataframe(
            filtered_study_plan,
            height = "content",
            column_order = None,
            hide_index = True
        )
    
    with sem2:
        
        st.subheader(f"Sem 2 ({study_campus[f"Year {year} Sem 2"]})")
        
        filtered_study_plan = study_plan[study_plan["Study Period"] == f"Year {year} Sem 2"].filter([study_campus[f"Year {year} Sem 2"], "Credits"])
        
        
        st.dataframe(
            filtered_study_plan,
            height = "content",
            column_order = None,
            hide_index = True
        )
# def update_study_plan():
#     st.session_state.study_plan[0] = pd.concat(
#                 [i for i in st.session_state.study_planner[0].values()], 
#                 ignore_index = True
#             )
    
# ---------------- Main App ----------------    
if __name__ == "__main__":
    st.set_page_config(
        page_title = "IDADM Course Information (HK)",
        layout="wide"
    )
    
    st.title("IDADM Course Information (HK)")
    st.info("It is applicable to students admitted in 2025/26 from CUHK ONLY", icon="ℹ️")
    
    
    if major_2 := select_major(data.major_list[1:]):
        st.caption("\\* Data updated as of 10 Jan 2026")
        st.caption("** This is unofficial. Please be aware that there may be mistakes.")
        
        # Hide the tabs if 2nd major is not selected
        ucore, major_1_tab, major_2_tab, planner = st.tabs(["University Core", "Interdisciplinary Data Analytics", major_2, "Planner"])

        with ucore:
            ucore_info()
        
        with major_1_tab:
            IDA_info(major_2)

        with major_2_tab:
            major_2_info(major_2)
        
        
        update_study_plan()
        with planner:
            if st.button("Refresh"):
                update_study_plan()   
                st.rerun()
                   
            y1, y2, y3, y4 = st.tabs(["Year 1", "Year 2", "Year 3", "Year 4"])
            with y1:
                show_planner(1)
            with y2:
                show_planner(2)
            with y3:
                show_planner(3)
            with y4:
                show_planner(4)
    