"""Upload -> inspect text -> extract -> review -> explicitly save."""
from hashlib import sha256
import os
import sqlite3

import streamlit as st
from pydantic import ValidationError

from assistant_core.cv import CVExtraction, CVProject, apply_cv, extract_cv, read_cv, redact_contacts
from assistant_core.profile import parse_skills, save_profile
from assistant_core.providers import Settings, ProviderError


def model_settings():
    def get(name, default=""):
        value = os.environ.get(name)
        if value is not None:
            return value
        try:
            return st.secrets.get(name, default)
        except FileNotFoundError:
            return default
    return Settings(get("LLM_PROVIDER", "compatible_api"), get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
                    get("LLM_MODEL", "openai/gpt-oss-20b"), get("LLM_API_KEY"))


def render_cv(workspace, profile, revision):
    st.subheader("Start with your CV")
    st.write("Upload your CV, review the extracted details, then save them to your profile.")
    uploaded = st.file_uploader("Upload CV", type=["pdf", "txt"], key=f"cv_upload_{workspace}",
                                help="Text-based PDF or UTF-8 TXT · up to 5 MB · up to 20 PDF pages. Scanned documents need OCR first.")
    if uploaded is None:
        return
    content = uploaded.getvalue()
    fingerprint = sha256(content).hexdigest()
    prefix = f"cv_{workspace}_{fingerprint}"
    try:
        text = redact_contacts(read_cv(uploaded.name, content))
    except ValueError as exc:
        st.error(str(exc))
        return
    st.caption("Common email and phone patterns are removed automatically. Check for remaining personal details and extraction errors below.")
    preview = st.text_area("Text to analyze — edit or remove private details", text, height=200, max_chars=30000, key=prefix+"_text")
    st.info("Extract profile sends the text above to your configured AI provider. The uploaded file is not saved. Your saved profile changes only after you approve the draft.")
    if st.button("Extract profile", type="primary", key=prefix+"_extract"):
        st.session_state.pop(prefix+"_draft", None)
        try:
            with st.spinner("Reading your experience and preparing a review draft…"):
                draft = extract_cv(model_settings(), preview)
            st.session_state[prefix+"_draft"] = {"data": draft.model_dump(), "text": preview, "revision": revision,
                                                  "nonce": st.session_state.get(prefix+"_nonce", 0) + 1}
            st.session_state[prefix+"_nonce"] = st.session_state[prefix+"_draft"]["nonce"]
        except (ProviderError, ValueError) as exc:
            st.error(str(exc))
    pending = st.session_state.get(prefix+"_draft")
    if not pending:
        return
    if preview != pending["text"]:
        st.warning("The source text changed. Extract again to create a matching draft.")
        return
    if pending["revision"] != revision:
        st.warning("Your profile changed after extraction. Extract again before saving this draft.")
        return
    draft = CVExtraction.model_validate(pending["data"])
    st.subheader("Review before saving")
    st.caption("Nonempty fields below replace the matching profile fields. Empty fields keep existing values. Projects are added; importing the same source again updates its matching projects. Availability is kept.")
    with st.form(prefix + f"_review_{pending['nonce']}"):
        name = st.text_input("Extracted name", draft.display_name, max_chars=120)
        headline = st.text_input("Extracted headline", draft.headline, max_chars=160)
        summary = st.text_area("Extracted summary", draft.summary, max_chars=5000)
        skills = st.text_area("Extracted skills (comma-separated)", ", ".join(draft.skills), max_chars=3000)
        education = st.text_area("Extracted education", draft.education, max_chars=5000)
        experience = st.text_area("Extracted experience", draft.experience, max_chars=10000)
        projects = []
        for index, project in enumerate(draft.projects):
            with st.expander(f"Project {index+1}: {project.title}", expanded=True):
                keep = st.checkbox("Include this project", value=True, key=prefix+f"_{pending['nonce']}_{index}_keep")
                title = st.text_input("Title", project.title, max_chars=160, key=prefix+f"_{pending['nonce']}_{index}_title")
                description = st.text_area("Description", project.description, max_chars=15000, key=prefix+f"_{pending['nonce']}_{index}_description")
                role = st.text_input("Role", project.role, max_chars=500, key=prefix+f"_{pending['nonce']}_{index}_role")
                tech = st.text_input("Technologies", ", ".join(project.technologies), key=prefix+f"_{pending['nonce']}_{index}_tech")
                st.caption("Source: " + project.source_quote)
                if keep:
                    projects.append(dict(title=title, description=description, role=role,
                                         technologies=parse_skills(tech), source_quote=project.source_quote))
        approved = st.checkbox("I reviewed these details and approve saving them to this profile")
        submitted = st.form_submit_button("Approve and save profile", type="primary")
    if submitted:
        if not approved:
            st.error("Review the draft and confirm approval before saving.")
            return
        try:
            reviewed = CVExtraction(display_name=name, headline=headline, summary=summary, skills=parse_skills(skills),
                                     education=education, experience=experience, projects=[CVProject(**p) for p in projects])
            updated = apply_cv(profile, reviewed, pending["text"])
            if not updated.display_name:
                st.error("Add your display name before saving.")
                return
            save_profile(workspace, updated, pending["revision"])
        except ValidationError:
            st.error("Check the project titles and descriptions; each description needs at least 20 characters.")
            return
        except (ValueError, sqlite3.Error, OSError):
            st.error("Could not save this draft. Reload if your profile changed in another session.")
            return
        st.session_state.pop(prefix+"_draft", None)
        st.session_state.profile_saved_notice = True
        st.rerun()
