"""Profile editor with an explicit, user-triggered CV extraction flow."""
import json
import sqlite3

import streamlit as st
from pydantic import ValidationError

from assistant_core.profile import Profile, Project, demo_profile, load_profile, parse_skills, save_profile
from cv_page import render_cv
from rag_ui import render_index


def render_profile():
    st.markdown('<div class="eyebrow">Workspace / My profile</div>', unsafe_allow_html=True)
    st.title("Put your experience in focus.")
    st.write("Build a clear record of your skills and the work that supports them.")
    selection = st.radio("Profile workspace", ["My real profile", "Synthetic demo"], horizontal=True)
    workspace = "demo" if selection == "Synthetic demo" else "personal"
    from assistant_core.database import database_url
    storage = "PostgreSQL" if database_url() else "local SQLite (development)"
    st.caption(f"Storage: {storage}. Manual edits stay on the app host; CV extraction uses your configured AI provider.")
    try:
        profile, revision = load_profile(workspace)
    except (ValueError, sqlite3.Error, OSError):
        st.error("Your saved profile could not be read. Check the local data folder; existing data has not been replaced.")
        return
    if workspace == "demo":
        st.warning("Synthetic workspace: this experience is invented and must not be presented as your real work.")
        if revision == 0 and st.button("Load synthetic profile"):
            save_profile("demo", demo_profile(), 0)
            st.rerun()
    if st.session_state.pop("profile_saved_notice", False):
        st.success("Changes saved.")
    one, two, three = st.columns(3)
    one.metric("Skills listed", len(profile.skills))
    two.metric("Projects saved", len(profile.projects))
    three.metric("Projects reviewed", sum(p.reviewed for p in profile.projects))
    upload, details, projects = st.tabs(["Upload CV", "Profile details", "Project evidence"])
    with upload:
        render_cv(workspace, profile, revision)
    with details:
        with st.form(f"details_{workspace}_{revision}"):
            name = st.text_input("Display name", profile.display_name, max_chars=120)
            headline = st.text_input("Professional headline", profile.headline, max_chars=160)
            summary = st.text_area("Experience summary", profile.summary, max_chars=5000,
                                   help="Describe your actual experience and the kind of work you deliver.")
            skills = st.text_area("Skills (separate with commas)", ", ".join(profile.skills), max_chars=3000)
            education = st.text_area("Education", profile.education, max_chars=5000)
            experience = st.text_area("Experience", profile.experience, max_chars=10000)
            hours = st.number_input("Available hours per week", min_value=0, max_value=168,
                                       value=profile.availability_hours_per_week)
            st.caption("0 means availability is not set. Pricing will be estimated separately for each job.")
            submitted = st.form_submit_button("Save profile", type="primary")
        if submitted:
            if not name.strip():
                st.error("Add a display name before saving.")
            else:
                updated = profile.model_copy(update={"display_name": name, "headline": headline,
                    "summary": summary, "skills": parse_skills(skills), "education": education, "experience": experience,
                    "availability_hours_per_week": hours})
                persist(workspace, updated, revision)
    with projects:
        st.subheader("The work behind your skills")
        st.caption("Record your role, deliverables and limits. Review each project before it becomes evidence for matching.")
        options = ["new"] + [p.id for p in profile.projects]
        labels = {p.id: p.title for p in profile.projects}
        chosen = st.selectbox("Choose a project", options, format_func=lambda x: "＋ Add a project" if x == "new" else labels[x],
                              key=f"project_choice_{workspace}")
        project = next((p for p in profile.projects if p.id == chosen), None)
        with st.form(f"project_{workspace}_{chosen}_{revision}"):
            title = st.text_input("Project title", project.title if project else "", max_chars=160)
            description = st.text_area("Project description and deliverables", project.description if project else "",
                                       height=180, max_chars=15000)
            role = st.text_input("Your role", project.role if project else "", max_chars=500)
            technologies = st.text_input("Technologies (separate with commas)", ", ".join(project.technologies) if project else "", max_chars=2000)
            outcomes = st.text_area("Verified outcomes", project.outcomes if project else "", max_chars=3000,
                                   help="Leave blank if no outcome was measured. Do not invent metrics.")
            limitations = st.text_area("Limitations / work not included", project.limitations if project else "", max_chars=3000)
            reviewed = st.checkbox("I reviewed this project description for accuracy", value=False,
                                   help="Confirm again whenever you save an edit. Demo evidence remains synthetic even when reviewed.")
            project_submitted = st.form_submit_button("Save project", type="primary")
        if project_submitted:
            try:
                values = dict(title=title, description=description, role=role, technologies=parse_skills(technologies),
                              outcomes=outcomes, limitations=limitations, reviewed=reviewed)
                if project:
                    values["id"] = project.id
                    values["source_quote"] = project.source_quote
                    values["source_id"] = project.source_id
                replacement = Project(**values)
                updated = profile.model_copy(deep=True)
                updated.projects = [replacement if p.id == chosen else p for p in updated.projects]
                if project is None:
                    updated.projects.append(replacement)
                persist(workspace, updated, revision)
            except ValidationError:
                st.error("Add a project title and a description of at least 20 characters.")
    st.divider()
    render_index(workspace)
    st.divider()
    st.download_button("Export profile JSON", json.dumps({"synthetic": workspace == "demo", "profile": profile.model_dump()}, indent=2),
                       file_name=f"{workspace}-profile.json", mime="application/json")
    st.caption("Use this profile's evidence index in Job analysis to assess fit with source citations.")


def persist(workspace, profile, revision):
    try:
        save_profile(workspace, profile, revision)
    except ValueError as exc:
        st.error(str(exc))
        return
    except (sqlite3.Error, OSError):
        st.error("Saving failed. Check that the local data folder is writable.")
        return
    st.session_state.profile_saved_notice = True
    st.rerun()
