"""Simple password gate for Streamlit Cloud deployment."""
import streamlit as st


def require_auth() -> None:
    """
    Show a centered login form until the correct password is entered.
    Password comes from st.secrets["app_password"].
    Call this at the TOP of every page (before any other st.* calls
    except set_page_config which must come first).
    """
    if st.session_state.get("authenticated"):
        return

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("## 💰 NetWorth Tracker")
        st.markdown("##### Sign in to continue")
        with st.form("login_form", clear_on_submit=True):
            pwd = st.text_input("Password", type="password", label_visibility="collapsed",
                                placeholder="Enter password…")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            expected = st.secrets.get("app_password", "")
            if pwd == expected:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password — try again.")

    st.stop()
