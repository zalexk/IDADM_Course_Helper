import streamlit as st
import data_retrieval as data
import pandas as pd

def select_major(major_list : tuple) -> str | None:
    major = st.selectbox(
        "2nd Major",
        major_list, 
        index = None,
        placeholder = "Select your second major")
    
    return major

def IDA_info(major_2 : str) -> None:
    for i in ("Faculty Package", "Required Courses"):
        st.subheader(i)
        
        course_table = pd.DataFrame(
            {
                "CUHK": data.show_course_info(
                        "Interdisciplinary Data Analytics",
                        data.get_course_list("Interdisciplinary Data Analytics")[i],
                        "hk"
                    ),
                
                "CUHKSZ": data.show_course_info(
                    "Interdisciplinary Data Analytics",
                    data.get_course_list("Interdisciplinary Data Analytics")[i],
                    "sz"
                )
            }
        )
        st.dataframe(course_table,
                    column_order = None,
                    hide_index = True,
                    height = "content")
    
    st.subheader("Elective Courses")
    
    st.info("""You have to take **6-15 units from Group A** + **12-21 units from Group B**
            
You have to take at least **12 units of courses from level 3000+** (including at least **6 units of courses from level 4000+**)
""")
    for i in ("A", "B"):
        st.markdown(f"**Group {i}**")
        elective_table = pd.DataFrame(
            {
                "CUHK": data.show_course_info(
                        "Interdisciplinary Data Analytics",
                        data.get_course_list(major_2)["1st Major Elective Courses"][i],
                        "hk"
                    ),
                
                "CUHKSZ": data.show_course_info(
                    "Interdisciplinary Data Analytics",
                    data.get_course_list(major_2)["1st Major Elective Courses"][i],
                    "sz"
                )
            }
        )
        
        st.dataframe(elective_table,
                    column_order = None,
                    hide_index = True,
                    height = "content")

def major_2_info(major_2 : str) -> None:
    st.info("Only the grade of the Research Component counts in the Major GPA for the Second Major")
    for i in ("Required Courses", "Research Component", "Elective Courses"):
        st.subheader(i)
        
        if i == "Elective Courses":
            i = "2nd Major Elective Courses"
            
        course_table = pd.DataFrame(
            {
                "CUHK": data.show_course_info(
                        major_2,
                        data.get_course_list(major_2)[i],
                        "hk"
                    ),
                
                "CUHKSZ": data.show_course_info(
                    major_2,
                    data.get_course_list(major_2)[i],
                    "sz"
                )
            }
        )
        
        st.dataframe(course_table,
                    column_order = None,
                    hide_index = True,
                    height = "content")
        
if __name__ == "__main__":
    st.set_page_config(
        page_title = "IDADM Course Information (HK)",
        layout="wide"
    )
    
    st.title("IDADM Course Information (HK)")
    st.info("It is applicable to students admitted in 2025/26 from CUHK ONLY", icon="ℹ️")
    st.caption("*Data updated as of 10 Jan 2026")
    st.caption("**This is unofficial. Please be aware that there may be mistakes.")
    
    if major_2 := select_major(data.major_list[1:]):
        # Hide the 1st major (Interdisciplinary Data Analytics) if 2nd major is not selected
        major_1_tab, major_2_tab = st.tabs(["Interdisciplinary Data Analytics", major_2])

        with major_1_tab:
            IDA_info(major_2)

        with major_2_tab:
            major_2_info(major_2)