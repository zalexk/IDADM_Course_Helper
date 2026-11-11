"""The "What's new" dialog for logged-in users."""

import streamlit as st

from src import storage
from src.announcements import Announcement


@st.dialog("What's new")
def show_dialog(entries : tuple[Announcement, ...]) -> None:
    """Show all unseen announcements in one dialog.

    Aggregating them avoids a popup storm when a user has been away for a few
    releases. "Got it" persists the highest version; "Later" only dismisses
    for this session, so the dialog returns on the next login.
    """
    if not entries:
        return

    for entry in entries:
        st.markdown(f"#### {entry.title}")
        if entry.date:
            st.caption(entry.date)
        if entry.body:
            st.markdown(entry.body)
        for item in entry.items:
            st.markdown(f"- {item}")

    st.divider()
    acknowledge_col, later_col = st.columns(2)

    if acknowledge_col.button("Got it", type="primary"):
        latest_version = max(entry.version for entry in entries)
        user_id = st.session_state.get("user_id")
        if user_id:
            try:
                storage.save_notice_version(user_id, latest_version)
            except Exception:
                st.error("Failed to save this notice, please try again.")
                return
            st.session_state.setdefault("user_config", {})[
                "notice_version"
            ] = latest_version
        st.session_state["notice_pending"] = ()
        st.rerun()

    if later_col.button("Later"):
        st.session_state["notice_pending"] = ()
        st.rerun()
