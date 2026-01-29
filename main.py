import streamlit as st
from src import data_retrieval as data
import pandas as pd

# ---------------- Config ----------------
if "study_plan" not in st.session_state:
    st.session_state.study_plan = [{}]
    # Store in session state
    
if "overall_study_plan" not in st.session_state:
    st.session_state.overall_study_plan = [pd.DataFrame(columns=["CUHK", "CUHKSZ", "Credits", "Study Period"])]
    
if "planner_update_count" not in st.session_state:
    st.session_state.planner_update_count = 0 
    

graduate_requirement = {
            "University Core" : {
                "Chinese Language" : 5,
                "English Language" : 8,
                "GE: Foundation Courses" : 6,
                "GE: Four Areas" : 7,
                "College GE" : 6,
                "Understanding China" : 1,
                "Hong Kong in the Wider Constitutional Order" : 1,
                "Digital Literacy and Computational Thinking" : 3,
                "Physical Education" : 2
            },
            "1st Major" : {
                "Faculty Package" : 9,
                "Required Courses" : 18,
                "COOP" : 3,
                "Elective" : 27,
                "Elective Group A" : 6,
                "Elective Group B" : 12,
                "Elective (3000+)" : 12,
                "Elective (4000)" : 6
            },
            "Total Credit" : 129
        }
    
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

study_period_col_config = {
                        "Study Period" : st.column_config.SelectboxColumn(
                            "Study Period",
                            options = list(study_campus.keys())
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

def update_requirement(major_2 : str):
    graduate_requirement["2nd Major"] = {
        "Required Courses" : data.get_major_2_requirement(major_2, "Required Courses"),
        "Research Component" : 3,
        "2nd Major Elective Courses" : data.get_major_2_requirement(major_2, "Elective Courses")
    }
    
    if "requirement_status" not in st.session_state:
        st.session_state.requirement_status = {
        "University Core": {_: False for _ in graduate_requirement["University Core"]},
        
        "1st Major": {_: [False, 0] for _ in graduate_requirement["1st Major"]},
        
        "2nd Major" : {_: [False, 0] for _ in graduate_requirement["2nd Major"]},
        
        "Total Credit": False 
    } # Default all the requirements are not fulfilled

def check_credit_limit(year : int, sem : int, total_credit : int):
    upper_limit = 18
    lower_limit = 9
    
    if sem == 3: # Stand for summer terms
        upper_limit = 6
        lower_limit = 0
    elif sem == 0: # Stand for the whole academic year
        upper_limit = 39
        lower_limit = 18
        
    elif year == 1:
        upper_limit = 19

    # Return True for within the limit
    if not(lower_limit <= total_credit <= upper_limit):
        st.error(f"""You are over / under the course load ({lower_limit} <= {total_credit} <= {upper_limit}).
                 
**Please submit relevant applications for the approval**.""")

def update_study_plan():
    """
    Concatenates all dataframes currently stored in study_planner[0].
    """
    if st.session_state.study_plan[0]:
        st.session_state.overall_study_plan[0] = pd.concat(
            [df for df in st.session_state.study_plan[0].values()],
            ignore_index=True
        )
def determine_level(course_id : str) -> int:
    if data.determine_campus(course_id) == "sz" :
        index = 3
    else:
        index = 4
    return int(course_id[index])

def ucore_info():
    course_list = data.get_course_list("University Core")["Required Courses"]
    
    course_table = pd.DataFrame(
        {
            "CUHK" : data.show_course_info("University Core", course_list, "hk"), 
            "CUHKSZ" : data.show_course_info("University Core", course_list, "sz"), 
            "Credits" : data.show_course_info("University Core", course_list, "hk", "credits"),
            "Study Period" : [" " for i in range(len(course_list))]
        }
    )
    # Create empty DataFrame for user input
    
    study_period_col_config["Credits"] = st.column_config.NumberColumn(
        "Credits",
        width = "small",
        required = True,
        min_value = 0,
        max_value = 10,
        step = "int"
    )
    
    st.session_state.study_plan[0]["University Core"] = st.data_editor(
        course_table.filter(["CUHK", "CUHKSZ", "Credits", "Study Period"]),
        num_rows = "dynamic",
        column_config = study_period_col_config,
        key = "ucore_data" # Add unique key
    )

    # Check the fulfillment of UCORE requirement
    ## Remove unplanned courses
    study_plan = st.session_state.study_plan[0]["University Core"]
    
    filter_study_plan = study_plan[study_plan["Study Period"].isin(list(study_campus.keys()))]
    
    ## Check GE: Foundation Courses
    GE_Foundation_Courses = {"UGFH1000 | In Dialogue with Humanity", "UGFN1000 | In Dialogue with Nature"}
    
    st.session_state.requirement_status["University Core"]["GE: Foundation Courses"] = GE_Foundation_Courses.issubset(set(filter_study_plan["CUHK"]))
    
    ## Check the remaining courses
    CORE_COURSE = {
        "Understanding China" : "UGCP1001 | Understanding China",
        "Hong Kong in the Wider Constitutional Order" : "UGCP1002 | Hong Kong in the Wider Constitutional Order",
        "Digital Literacy and Computational Thinking" : "ENGG1003 | Digital Literacy and Computational Thinking"
        }
    
    for item in CORE_COURSE.keys():
        st.session_state.requirement_status["University Core"][item] = CORE_COURSE[item] in set(filter_study_plan["CUHK"])
        
    
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
        
        st.session_state.study_plan[0][f"IDA - {i}"] = st.data_editor(
            course_table.filter(["CUHK", "CUHKSZ", "Credits", "Study Period"]),
            column_order = None,
            hide_index = True,
            height = "content",
            column_config = study_period_col_config,
            disabled = ["CUHK", "CUHKSZ", "Credits"],
            key = f"IDA_{i}_data"
        )
        
        # Auto-check completion
        if i != "COOP": # Exclude COOP as it is compulsory
            # Remove unplanned courses
            study_plan = st.session_state.study_plan[0][f"IDA - {i}"]
            filtered_study_plan = study_plan[study_plan["Study Period"].isin(list(study_campus.keys()))]
            
            st.session_state.requirement_status["1st Major"][i] = [
                len(study_plan) == len(filtered_study_plan), # Determine True / False
                filtered_study_plan["Credits"].sum() # Calculate total credits
            ]
        else:
            st.session_state.requirement_status["1st Major"]["COOP"] = [True, 3]
            # As field trips are compulsory
    
    st.subheader("Elective Courses")
    
    st.info("""Requirement: 6-15 units from Group A + 12-21 units from Group B
            
At least 12 units level 3000+ (incl 6 units level 4000+)
""")
    elective_study_plan = pd.DataFrame(columns=["CUHK", "CUHKSZ", "Credits", "Study Period"]) 
    # Create an empty DataFrame
    
    for i in ("A", "B"):
        st.markdown(f"**Group {i}**")
        
        course_list = data.get_course_list(major_2)["1st Major Elective Courses"][i]
        
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
                "Credits": data.show_course_info(
                    "Interdisciplinary Data Analytics",
                    course_list,
                    "sz",
                    "credits"
                ),
                "Study Period" : [" " for _ in range(len(course_list))]
            }
        )
        
        st.session_state.study_plan[0][f"IDA - {i}"] = st.data_editor(
            course_table.filter(["CUHK", "CUHKSZ", "Credits", "Study Period"]),
            column_order = None,
            hide_index = True,
            height = "content",
            column_config = study_period_col_config,
            disabled = ["CUHK", "CUHKSZ", "Credits"],
            key = f"IDA_Elective_{i}"
        )
        
        # Auto-check completion
        study_plan = st.session_state.study_plan[0][f"IDA - {i}"]
        # Remove unplanned courses
        filtered_study_plan = study_plan[study_plan["Study Period"].isin(list(study_campus.keys()))]
        
        finished_credits = filtered_study_plan["Credits"].sum() # Calculate total credits
            
        st.session_state.requirement_status["1st Major"][f"Elective Group {i}"] = [
            finished_credits >= graduate_requirement["1st Major"][f"Elective Group {i}"], # Determine True / False
            finished_credits 
        ]
        
        elective_study_plan = pd.concat(
            [elective_study_plan, filtered_study_plan],
            ignore_index=True
        ) # Combine Group A and Group B

    # Auto-check completion
    finished_credits = elective_study_plan["Credits"].sum() # Calculate total credits
    
    st.session_state.requirement_status["1st Major"]["Elective"] = [
        finished_credits >= graduate_requirement["1st Major"]["Elective"],
        finished_credits
    ]
    
    # Calculate the credits of level 3000 & 4000 courses
    elective_course_list_by_group = data.get_course_list(major_2)["1st Major Elective Courses"]

    # Combine course list of Group A and B
    elective_course_list = elective_course_list_by_group["A"] + elective_course_list_by_group["B"]
    
    elective_course_dict_by_level = {
        3 : [],
        4 : []
    }
    
    # Group by level
    for id in elective_course_list:
        level = determine_level(id)
        if 3 <= level <= 4:
            elective_course_dict_by_level[level].append(id)
    
    level_4_course = data.show_course_info(
        major_2, 
        elective_course_dict_by_level[4],
        campus = "hk"
    )
    
    level_3_course = data.show_course_info(
        major_2, 
        elective_course_dict_by_level[3],
        campus = "hk"
    )
    
    level_4_df = elective_study_plan[elective_study_plan["CUHK"].isin(level_4_course)]
    level_4_credit = level_4_df["Credits"].sum()
    
    st.session_state.requirement_status["1st Major"][f"Elective (4000)"] = [
            level_4_credit >= graduate_requirement["1st Major"]["Elective (4000)"], 
            level_4_credit 
        ]
    
    
    level_3_df = elective_study_plan[elective_study_plan["CUHK"].isin(level_3_course)]
    level_3_or_above_credit = level_3_df["Credits"].sum() + level_4_credit
    
    st.session_state.requirement_status["1st Major"][f"Elective (3000+)"] = [
            level_3_or_above_credit >= graduate_requirement["1st Major"]["Elective (3000+)"], 
            level_3_or_above_credit 
        ]

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
        
        st.session_state.study_plan[0][f"2nd Major - {i}"] = st.data_editor(
            course_table.filter(["CUHK", "CUHKSZ", "Credits", "Study Period"]),
            column_order = None,
            hide_index = True,
            height = "content",
            column_config = study_period_col_config,
            disabled = ["CUHK", "CUHKSZ", "Credits"],
            key = f"major_2_{i}"
        )
        
        # Auto-check completion
        study_plan = st.session_state.study_plan[0][f"2nd Major - {i}"]
        # Remove unplanned courses
        filtered_study_plan = study_plan[study_plan["Study Period"].isin(list(study_campus.keys()))]
        
        if i != "2nd Major Elective Courses": 
            st.session_state.requirement_status["2nd Major"][i] = [
                len(study_plan) == len(filtered_study_plan), # Determine True / False
                filtered_study_plan["Credits"].sum() # Calculate total credits
            ]
        else:
            finished_credits = filtered_study_plan["Credits"].sum() # Calculate total credits
            
            st.session_state.requirement_status["2nd Major"][i] = [
                finished_credits >= graduate_requirement["2nd Major"]["2nd Major Elective Courses"], # Determine True / False
                finished_credits 
            ]
       
def show_planner(year : int):
    study_plan = st.session_state.overall_study_plan[0] # Get the overall study plan

    sem1_period = f"Year {year} Sem 1"
    sem2_period = f"Year {year} Sem 2"

    sem1_campus = study_campus[sem1_period]
    sem2_campus = study_campus[sem2_period]

    periods_for_year = [sem1_period, sem2_period]

    sem1, sem2 = st.columns(2)

    with sem1:
        st.subheader(f"Sem 1 ({sem1_campus})")
        
        filtered_study_plan = study_plan[study_plan["Study Period"] == sem1_period].filter([sem1_campus, "Credits"])
        total_credit = filtered_study_plan["Credits"].sum()
        
        check_credit_limit(year, 1, total_credit)
            
        
        st.dataframe(
            filtered_study_plan,
            height = "content",
            column_order = None,
            hide_index = True
        )

        
        st.metric("Total Credits", 
                value = total_credit
                )

    with sem2:
        st.subheader(f"Sem 2 ({sem2_campus})")

        filtered_study_plan = study_plan[study_plan["Study Period"] == sem2_period].filter([sem2_campus, "Credits"])
        
        total_credit = filtered_study_plan["Credits"].sum()
        check_credit_limit(year, 2, total_credit)
        
        st.dataframe(
            filtered_study_plan,
            height = "content",
            column_order = None,
            hide_index = True
        )
        st.metric("Total Credits", 
              value = total_credit
            )
        
    # Summer terms
    if year < 4:
        summer_periods = [
            f"Year {year} Summer (CUHK)", 
            f"Year {year} Summer (CUHKSZ)"
        ]
        periods_for_year.extend(summer_periods)

        st.subheader("Summer Session")
        filtered_study_plan = study_plan[study_plan["Study Period"].isin(summer_periods)].filter(["CUHK", "CUHKSZ", "Credits"])

        total_credit = filtered_study_plan["Credits"].sum()
        check_credit_limit(year, 3, total_credit)
        # 3 stands for summer terms
        
        left, right = st.columns(2)
        with left:
            st.dataframe(
                filtered_study_plan,
                height = "content",
                column_order = None,
                hide_index = True
            )
        with right:
            st.metric("Total Credits", 
                value = total_credit
                )

    # Show total credits per year
    filtered_study_plan = study_plan[study_plan["Study Period"].isin(periods_for_year)].filter(["CUHK", "CUHKSZ", "Credits"])   
    
    total_credit = filtered_study_plan["Credits"].sum()
    check_credit_limit(year, 0, total_credit) 
    # 0 stands for the whole academic year

    st.metric("**Total Credits for the Year**", 
        value = total_credit
        )
    
def show_requirement(major_2 : str):
    st.header("Graduation Requirements")
    
    ucore, major = st.columns(2)
    
    ## ---------------- Check UCore Requirement ---------------- 
    with ucore:
        st.subheader("University Core")
        # Display requirements status
        ucore_requirement = graduate_requirement["University Core"]
        
        ucore_df = pd.DataFrame(
            {
                "Item" : ucore_requirement.keys(),
                "Requirement" : ucore_requirement.values(),
                "Fulfil" : st.session_state.requirement_status["University Core"].values()
            }
        )
        ucore_requirement_status = st.data_editor(
            ucore_df,
            disabled = ["Item", "Requirement"],
            hide_index = True
        )        
    with major:
        ## ---------------- Check 1st major requirement ---------------- 
        st.subheader("1st Major (IDA)")
        major_1_requirement = graduate_requirement["1st Major"]
        major_1_requirement_df = pd.DataFrame(
            {
                "Item" : major_1_requirement.keys(),
                "Requirement" : major_1_requirement.values(),
                "Credits" : [i[1] for i in st.session_state.requirement_status["1st Major"].values()],
                
                "Fulfil" : [i[0] for i in st.session_state.requirement_status["1st Major"].values()]
            }
        )
        st.session_state.requirement_status["1st Major"].values()
        st.dataframe(
            major_1_requirement_df,
            hide_index = True
        )
        
        ## ---------------- Check 2nd major requirement ----------------    
        st.subheader(f"2nd Major ({major_2})")
        major_2_requirement = graduate_requirement["2nd Major"]
        major_2_requirement_df = pd.DataFrame(
            {
                "Item" : major_2_requirement.keys(),
                "Requirement" : major_2_requirement.values(),
                "Credits" : [i[1] for i in st.session_state.requirement_status["2nd Major"].values()],
                
                "Fulfil" : [i[0] for i in st.session_state.requirement_status["2nd Major"].values()]
            }
        )
        st.dataframe(
            major_2_requirement_df,
            hide_index = True
        )

def show_overall():
    st.info("It is used to export your study plan into `.csv` format.")
    st.dataframe(
        st.session_state.overall_study_plan[0],
        height = "content",
        column_order = None,
        hide_index = True
    )

# ---------------- Main App ----------------    
if __name__ == "__main__":
    st.set_page_config(
        page_title = "IDADM Course Information (HK)",
        layout="wide"
    )
    
    st.title("IDADM Course Information (HK)")
    st.info("It is applicable to students admitted in 2025/26 from CUHK ONLY", icon="❗")
    
    
    if major_2 := select_major(data.major_list[2:]):
        update_requirement(major_2)
        
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
            y1, y2, y3, y4, grad_requirement, overall = st.tabs(["Year 1", "Year 2", "Year 3", "Year 4", "Graduation Requirements", "Overall"])
            with y1:
                show_planner(1)
            with y2:
                show_planner(2)
            with y3:
                show_planner(3)
            with y4:
                show_planner(4)
            with grad_requirement:
                show_requirement(major_2)
            with overall:
                show_overall()
    
