"""Simple password gate for Streamlit Cloud deployment."""
# ── SSL fix — must run before any network call ────────────────────────────────
# On Windows, Python's built-in SSL store often can't verify Google's CA.
# Patch ssl.create_default_context() to use certifi's trusted CA bundle so
# every HTTPS connection (gspread, google-auth, requests) validates correctly.
try:
    import os, ssl, certifi as _certifi

    _CA = _certifi.where()

    # 1. Point requests / urllib3 at certifi (picked up before first connection)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _CA)
    os.environ.setdefault("SSL_CERT_FILE",       _CA)

    # 2. Patch the stdlib ssl module so httplib / urllib also use certifi
    _orig_ctx = ssl.create_default_context

    def _patched_ctx(*args, **kwargs):
        if not any(k in kwargs for k in ("cafile", "capath", "cadata")):
            kwargs["cafile"] = _CA
        return _orig_ctx(*args, **kwargs)

    ssl.create_default_context = _patched_ctx
except Exception:
    pass   # never crash the app over a cert patch
# ─────────────────────────────────────────────────────────────────────────────

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
