import streamlit as st
from app import constant, ucore, ida, major_2, planner, login
import src.data_retrieval as data


@st.cache_data
def load_cache_data() -> data.CourseDataContext:
    return data.load_all_data()

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
    
    is_guest = "login_status" not in st.session_state or st.session_state["login_status"] is False
    if is_guest:
        st.warning(
            "Please log in (sidebar) to save and view your study plan."
            "Any selections made before logging in will be discarded on login. "
            "You cannot use Planner Function before logging in.",
            icon="🔒",
        )
        if login.has_guest_edits() and not st.session_state.get("guest_notice_shown"):
            login.guest_edits_notice()
        with st.sidebar:
            login.ui()
    major_2nd = st.selectbox(
        "2nd Major",
        constant.MAJOR_2nd_list,
        index = None,
        placeholder = "Select your second major"
    )
    
    try:
        context = load_cache_data()
        
    except data.FileMissingError as e:
        st.error(f"File Not Found: {e}")
        st.stop()
        
    except data.DataFormatError as e:
        st.error(f"Wrong File Format: {e}")
        st.stop()
        
    if major_2nd: # Display only when 2nd major is selected
        st.caption("\\* Data updated as of 10 Jan 2026")
        st.caption("** This is unofficial. Please be aware that there may be mistakes.")
        st.caption("*** It is applicable to students admitted in 2025/26 from CUHK ONLY")
        
        ucore_tab, major_1_tab, major_2_tab, planner_tab = st.tabs(
            [
                "University Core", 
                "Interdisciplinary Data Analytics", 
                major_2nd, 
                "Planner"
            ]
        )
        
        with ucore_tab:
            ucore.ui(context)

        with major_1_tab:
            ida.ui(context, major_2nd)

        with major_2_tab:
            major_2.ui(context, major_2nd)

        with planner_tab:
            planner.ui(context, major_2nd)