import streamlit as st
from src import auth
import time

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
                        time.sleep(1) # To show successful login
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
                else:
                    st.error("Wrong username or password")
                    
            except auth.AuthServiceError:
                st.error("Sign in failed")   

    if st.button("Sign Up"):
        signup_ui()