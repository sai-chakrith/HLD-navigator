import json

import requests
import streamlit as st

st.set_page_config(page_title="HLD Navigator", layout="wide")
st.title("HLD Navigator · AUTOSAR HLD Review")
st.caption("Engineering pilot · Exact source excerpts by default · Human-reviewed architecture")
base = st.sidebar.text_input("API", "http://127.0.0.1:8010").rstrip("/")
workspace = st.sidebar.text_input("Workspace", "pilot")
token = st.sidebar.text_input("Individual access token", type="password")


def call(method, path, **kwargs):
    try:
        response = requests.request(
            method,
            f"{base}/workspaces/{workspace}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        st.error(str(error))
        if getattr(error, "response", None) is not None:
            st.code(error.response.text)
        st.stop()


if not token:
    st.info("Provision a user using the README, then enter their token.")
    st.stop()

upload, review, search, report = st.tabs(["Upload", "Review", "Search", "Report / Compare"])
with upload:
    with st.form("upload"):
        title = st.text_input("Document title", "Powertrain HLD")
        version = st.text_input("Version", "1.0")
        file = st.file_uploader("PDF, Markdown or text", type=["pdf", "md", "txt"])
        if st.form_submit_button("Extract proposals") and file:
            result = call(
                "POST",
                "/documents",
                data={"title": title, "version": version},
                files={"file": (file.name, file.getvalue())},
            )
            st.json(result)
            st.success("Stored with source evidence. Review warnings and every proposal.")
documents = call("GET", "/documents")
if not documents:
    st.info("Upload examples/powertrain.md to start.")
    st.stop()
labels = {d["id"]: f"{d['title']} · {d['version']}" for d in documents}
with review:
    selected = st.selectbox("Source revision", list(labels), format_func=labels.get)
    document = next(d for d in documents if d["id"] == selected)
    st.json(document)
    reason = st.text_input("Source review reason", "Reviewed source and extraction warnings")
    approve, revoke = st.columns(2)
    for column, text, value in [
        (approve, "Approve source", True),
        (revoke, "Revoke source", False),
    ]:
        if column.button(text):
            call(
                "POST", f"/documents/{selected}/review", json={"approved": value, "reason": reason}
            )
            st.rerun()
    for entity in call("GET", "/entities", params={"document_id": selected}):
        with st.expander(f"{entity['kind']}: {entity['name']} — {entity['status']}"):
            st.code(entity["evidence"])
            st.json(entity["location"])
            with st.form(entity["id"]):
                attributes = st.text_area(
                    "Attributes (JSON)", json.dumps(entity["attributes"], indent=2)
                )
                status = st.selectbox("Decision", ["approved", "rejected"])
                reason = st.text_input("Reason", "Checked against source")
                if st.form_submit_button("Save reviewer decision"):
                    try:
                        parsed = json.loads(attributes)
                    except json.JSONDecodeError:
                        st.error("Attributes must be valid JSON")
                    else:
                        call(
                            "POST",
                            f"/entities/{entity['id']}/review",
                            json={"status": status, "attributes": parsed, "reason": reason},
                        )
                        st.rerun()
with search:
    selected = st.selectbox("Search revision", list(labels), format_func=labels.get)
    question = st.text_input("Question", "Which component provides vehicle speed?")
    if st.button("Find approved evidence"):
        result = call("POST", "/query", json={"text": question, "document_id": selected})
        st.caption(result["mode"])
        st.text(result["answer"])
        for index, evidence in enumerate(result["evidence"], 1):
            with st.expander(f"[{index}] {evidence['title']} · {evidence['version']}"):
                st.code(evidence["text"])
                st.json(evidence["location"])
with report:
    selected = st.selectbox("Export revision", list(labels), format_func=labels.get)
    if st.button("Build reviewed report"):
        result = call("GET", "/export", params={"document_id": selected})
        st.json(result)
        st.download_button(
            "Download JSON", json.dumps(result, indent=2), "architecture.json", "application/json"
        )
    before = st.selectbox("Before", list(labels), format_func=labels.get)
    after = st.selectbox("After", list(labels), format_func=labels.get)
    if st.button("Compare approved inventories"):
        st.json(call("GET", "/compare", params={"before": before, "after": after}))
