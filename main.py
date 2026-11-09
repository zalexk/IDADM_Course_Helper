import streamlit as st
from app import constant, ucore, ida, major_2, planner, login
import src.data_retrieval as data


@st.cache_data
def load_cache_data(cache_version : int) -> data.CourseDataContext:
    # cache_version is part of the @st.cache_data key (see
    # constant.DATA_CACHE_VERSION): bump it when data/*.json changes so a
    # running app does not keep serving a stale CourseDataContext.
    return data.load_all_data()

if __name__ == "__main__":
    st.set_page_config(
        page_title = "IDADM Course Helper (HK)",
        layout="wide"
    )
    
    st.title("IDADM Course Helper (HK)")
    
    
    
    is_guest = "login_status" not in st.session_state or st.session_state["login_status"] is False
    if is_guest:
        st.warning(
            "Please log in from the sidebar to save and view your study plan. "
            "Any selections made before logging in will be discarded when you log in. "
            "You cannot use the Planner until you log in.",
            icon="🔒",
        )
        if login.has_guest_edits() and not st.session_state.get("guest_notice_shown"):
            login.guest_edits_notice()
        with st.sidebar:
            login.ui()
            
    caption, changelog = st.columns(2)
    with caption:
        st.link_button(
            "使用指南 User Guide",
            "https://idadm.notion.site/userguide"
        )
        st.caption("\\* Data updated as of 19 Oct 2026 ([See the changes](https://idadm.notion.site/study-scheme-change))")
        st.caption("** This is unofficial. Please be aware that there may be mistakes.")
        st.caption("*** It is applicable only to students admitted to CUHK in 2025/26.")
        st.caption("If you encounter any bugs, please contact me via [email](mailto:alex-zsk@link.cuhk.edu.hk) or [GitHub Issues](https://github.com/zalexk/IDADM_Course_Helper/issues).")
    
        
    with changelog:
        with st.expander("Read what’s new `v1.2.1`"):
            st.markdown("**`v1.2.1`:** Update the revised UCore GE graduation requirement")
            st.markdown("**`v1.2.0`:** Support planning courses outside the curriculum")
            st.markdown("**`v1.1.1`:** Update to the latest substitute course list")
            st.markdown("**`v1.1`:** Add a course import function; add Chinese Language and English Language courses")
            st.markdown("**`v1.0`:** Add a login function to save your study plan")

        st.caption("The revisions to General Education have already been updated on the website. The detailed arrangement is summarized [here](https://idadm.notion.site/Revision-to-General-Education-40d0912b765c804f9126eaa7d0555c84?source=copy_link).")
        st.caption("The official substitute course list has already been updated ([See the change](https://cuhk-course-equivalence-ry7ev48ni8s.qoder.zone)). The website has already been updated.")
        
            
    major_2nd = st.selectbox(
        "2nd Major",
        constant.MAJOR_2nd_list,
        index = None,
        placeholder = "Select your second major"
    )
    
    try:
        context = load_cache_data(constant.DATA_CACHE_VERSION)
        
    except data.FileMissingError as e:
        st.error(f"File Not Found: {e}")
        st.stop()
        
    except data.DataFormatError as e:
        st.error(f"Wrong File Format: {e}")
        st.stop()

    if major_2nd: # Display only when 2nd major is selected
        

        
        ucore_tab, major_1_tab, major_2_tab, planner_tab = st.tabs(
            [
                "University Core", 
                "Interdisciplinary Data Analytics", 
                major_2nd, 
                "Planner"
            ],
            key="main-tabs", # active tab survives rerun/refresh (session_state)
        )

        
        with ucore_tab:
            ucore.ui(context, major_2nd)

        with major_1_tab:
            ida.ui(context, major_2nd)

        with major_2_tab:
            major_2.ui(context, major_2nd)

        with planner_tab:
            planner.ui(context, major_2nd)