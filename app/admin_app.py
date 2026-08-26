"""
admin_app.py
------------
Streamlit admin portal for EasyGov Nepal.

Lets an administrator:
  * edit a service's catalog fields and guidance (auto re-indexes into the RAG
    vector store so the chatbot reflects the change), and
  * ingest new/updated versioned source documents (PDF/MD) for the RAG pipeline.

Run:
    streamlit run app/admin_app.py
Configure the backend address (default http://127.0.0.1:8000) and the
ADMIN_TOKEN (same value as the server's .env) in the sidebar.
"""

import base64
import os
import requests
import streamlit as st

st.set_page_config(page_title="EasyGov Admin", page_icon="🛠️", layout="wide")

DEFAULT_BACKEND = os.getenv("EASYGOV_ADMIN_BACKEND", "http://127.0.0.1:8000")


def _headers(token: str) -> dict:
    return {"X-Admin-Token": token}


def fetch_services(base: str, token: str):
    """Return (services, error_message). Distinguishes connectivity from auth."""
    try:
        r = requests.get(f"{base}/admin/services", headers=_headers(token), timeout=60)
    except requests.exceptions.ConnectionError:
        return None, f"Could not reach the backend at {base}. Is the server running?"
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {e}"
    if r.status_code == 503:
        return None, "The server reports that ADMIN_TOKEN is not configured (503). Add it to .env and restart the server."
    if r.status_code == 401:
        return None, "Wrong admin token (401). It must match ADMIN_TOKEN in the server's .env."
    if r.status_code != 200:
        return None, f"Unexpected response: HTTP {r.status_code}"
    return r.json(), None


# ── Sidebar config ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Admin settings")
    backend = st.text_input("Backend address", value=DEFAULT_BACKEND).strip().rstrip("/")
    token = st.text_input("Admin token", type="password").strip()
    st.caption("This must match ADMIN_TOKEN in the server's .env file.")

services, auth_error = (fetch_services(backend, token) if token else (None, None))

if token and auth_error:
    st.error(auth_error)
    st.stop()

if services is None:
    st.title("🛠️ EasyGov Admin Portal")
    st.info("Enter the backend address and admin token in the sidebar to continue.")
    st.stop()

tab_services, tab_ingest = st.tabs(["📝 Services & Guidance", "📄 Ingest Documents"])

# ── Tab: services & guidance (dashboard guidance page ONLY — no RAG) ─────────
with tab_services:
    st.header("Services & Guidance")
    st.caption("Edit a service's catalog fields and the guidance shown on the app's guide page. RAG is not touched here — use the 'RAG Ingest' tab to update the chatbot's knowledge.")

    options = {f"{s['title']} (id {s['id']})": s for s in services}
    sel = st.selectbox("Select service", list(options.keys()))
    if not sel:
        st.stop()
    svc = options[sel]
    sid = svc["id"]

    # Fetch the full detail to prefill the form.
    detail = None
    try:
        detail = requests.get(
            f"{backend}/api/v1/services/{sid}?lang=en", headers=_headers(token), timeout=60
        ).json().get("service", {})
    except requests.RequestException:
        pass

    detail = detail or {}

    with st.form(f"edit_{sid}"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Title (EN)", value=detail.get("title", ""))
            category = st.text_input("Category (EN)", value=detail.get("category", ""))
        with col2:
            department = st.text_input("Department", value=detail.get("department") or "")
            estimated_days = st.number_input("Estimated days", value=int(detail.get("estimated_days") or 0), min_value=0)
            fee_npr = st.number_input("Fee (NPR)", value=int(detail.get("fee_npr") or 0), min_value=0)
            is_active = st.checkbox("Active", value=not bool(detail.get("is_active", True) is False))

        description = st.text_area("Description (EN)", value=detail.get("description") or "", height=90)
        guidance = st.text_area("Guidance (EN)", value=detail.get("guidance") or "", height=220)
        submitted = st.form_submit_button("💾 Save Guidance")

    if submitted:
        # Note: Nepali (NE) fields are intentionally not edited here — they come
        # back empty from the detail endpoint, and sending them would overwrite
        # the existing translations with blank values.
        payload = {
            "title": title, "category": category,
            "description": description,
            "guidance": guidance,
            "department": department, "estimated_days": int(estimated_days), "fee_npr": int(fee_npr),
            "is_active": is_active,
        }
        try:
            r = requests.post(f"{backend}/admin/services/{sid}", json=payload, headers=_headers(token), timeout=120)
            r.raise_for_status()
            st.success("Guidance saved. The app's guide page is updated.")
        except requests.RequestException as e:
            st.error(f"Save failed: {e}")

# ── Tab: RAG ingest (new file versions → chatbot knowledge) ───────────────────
with tab_ingest:
    st.header("RAG Ingest — New File Versions")
    st.caption("Upload a new/updated PDF or Markdown guide for a service. This drives the chatbot's knowledge (RAG). 'Replace previous version' removes the older source files for that folder first.")

    with st.form("ingest"):
        col1, col2 = st.columns(2)
        with col1:
            folder = st.text_input("Service folder", value="passport").strip().lower()
            version = st.text_input("Version", value="1.0").strip()
        with col2:
            replace_prev = st.checkbox("Replace previous version", value=False)
            upload = st.file_uploader("Document (PDF or Markdown)", type=["pdf", "md"])
        go = st.form_submit_button("🚀 Ingest")

    if go and upload:
        files = {"file": (upload.name, upload.getvalue(), upload.type or "application/octet-stream")}
        data = {"service": folder, "version": version, "replace_previous": str(replace_prev).lower()}
        try:
            r = requests.post(f"{backend}/admin/ingest", data=data, files=files, headers=_headers(token), timeout=180)
            r.raise_for_status()
            res = r.json()
            st.success(f"Ingested {res.get('indexed', 0)} chunks for '{res.get('service')}' (v{res.get('version')}).")
            st.json(res.get("stats"))
        except requests.RequestException as e:
            st.error(f"Ingest failed: {e}")
    elif go and not upload:
        st.warning("Choose a file to upload.")

    st.divider()
    st.markdown("**Existing service folders** (derived from service titles, ASCII): `citizenship`, `nid`, `passport`, `driving_license`, ... You may also create a new folder name.")
