import streamlit as st
from app import constant, ucore

if __name__ == "__main__":
    st.set_page_config(
        page_title = "IDADM Course Helper (HK)",
        layout="wide"
    )
    
    st.title("IDADM Course Helper (HK)")
    
    st.link_button(
        "使用指南 User Guide",
        "https://alex-zsk.notion.site/userguide"
    )
    
    major_2nd = st.selectbox(
        "2nd Major",
        constant.MAJOR_2nd_list,
        index = None,
        placeholder = "Select your second major"
    )
    
    if major_2nd: # Display only when 2nd major is selected
        st.caption("\\* Data updated as of 10 Jan 2026")
        st.caption("** This is unofficial. Please be aware that there may be mistakes.")
        st.caption("*** It is applicable to students admitted in 2025/26 from CUHK ONLY")
        
        ucore_tab, major_1_tab, major_2_tab, planner_tab = st.tabs(["University Core", "Interdisciplinary Data Analytics", major_2nd, "Planner"])
        
        with ucore_tab:
            ucore.ui()