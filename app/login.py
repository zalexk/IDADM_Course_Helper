import streamlit as st
from src import auth
import time

# Element-key prefixes for every data_editor across all tabs.
# On login we purge any guest-edited widget state so it cannot leak into the
# logged-in user's DB rows (design doc R5: guest edited_rows residue).
_EDITOR_KEY_PREFIXES = ("ucore-", "ida-", "major2-")


def _clear_editor_state() -> None:
    """Delete all data_editor widget state so tables rebuild from DB after login."""
    for key in list(st.session_state.keys()):
        if key.startswith(_EDITOR_KEY_PREFIXES) or key == "guest_notice_shown":
            del st.session_state[key]


def has_guest_edits() -> bool:
    """True if any data_editor has unsaved guest edits (edited/added/deleted rows)."""
    for key in st.session_state:
        if not key.startswith(_EDITOR_KEY_PREFIXES):
            continue
        state = st.session_state[key]
        if (state.get("edited_rows") or state.get("added_rows")
                or state.get("deleted_rows")):
            return True
    return False

@st.dialog("Unsaved Edits")
def guest_edits_notice():
    st.warning(
        "You have made edits without logging in. "
        "These edits will be discarded when you log in.",
        icon="⚠️",
    )
    if st.button("OK, got it"):
        st.session_state["guest_notice_shown"] = True
        st.rerun()

@st.dialog("Signup")
def signup_ui():
    with st.form("signup"):
        username = st.text_input("Username", placeholder = "Input your username")
                
        password = st.text_input(
            "Password", 
            type =  "password",
            autocomplete = "password",
            placeholder = "Minimum 8 characters with uppercase and lowercase"
        )
        
        submit = st.form_submit_button("Signup")
        
        if submit and username and password:
            if auth.validate_password_strength(password): # Check password's strength
                try:
                    if user_id := auth.signup(username, password):
                        st.success("Successful Signup")
                        st.session_state["user_id"] = user_id
                        st.session_state["login_status"] = True
                        _clear_editor_state()
                        st.rerun()
                        
                    else: # when auth.signup returns None
                        st.error("Username is repeated")
                
                except auth.AuthServiceError:
                    st.error("Signup failed, please try again.")

            
            else:
                st.error("Please use stronger password (Minimum 8 characters with uppercase and lowercase)")

            

def ui():
    with st.form("login"):
        username = st.text_input("Username", placeholder = "Input your username")
        
        password = st.text_input(
            "Password", 
            type =  "password",
            autocomplete = "password",
            placeholder = "Input your password"
        )
        
        submit = st.form_submit_button("Login")
        
        if submit:
            try:
                user_id = auth.signin(username, password)
                
                if user_id:
                    st.session_state["login_status"] = True
                    st.success("Successful Login")
                    st.session_state["user_id"] = user_id
                    _clear_editor_state() # purge guest edits so they can't leak into the logged-in user's DB rows
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Wrong username or password")
                    
            except auth.AuthServiceError:
                st.error("Sign in failed")   

    if st.button("Sign Up"):
        signup_ui()