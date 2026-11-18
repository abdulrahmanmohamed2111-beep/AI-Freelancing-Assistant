import json
import os
import time
from functools import partial

import streamlit as st

from assistant_core.providers import ProviderError, Settings, generate
from assistant_core.sample import SAMPLE_ANALYSIS, SAMPLE_JOB
from assistant_core.workflow import build_graph
from ui import evidence_card, styles
from profile_page import render_profile
from rag_ui import render_match
from assistant_core.profile import load_profile
from assistant_core.rag import retrieve
from assistant_core.matching import match_requirements
from assistant_core.runs import persist_match

st.set_page_config(page_title="Freelance AI | Job analysis", page_icon="🔎", layout="wide")
styles()


def setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        return str(st.secrets.get(name, default))
    except FileNotFoundError:
        return default


with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-icon">f.</span>Freelance AI</div>'
                '<div class="eyebrow">Workspace</div>', unsafe_allow_html=True)
    page = st.selectbox("Open page", ["Job analysis", "My profile"], key="workspace_page")
    st.markdown(
                '<div class="eyebrow">Coming next</div>'
                '<div class="roadmap">Proposals <small>PLANNED</small></div>'
                '<div class="roadmap">Applications <small>PLANNED</small></div>', unsafe_allow_html=True)
    st.divider()
    if page == "Job analysis":
        mode = st.radio("Analysis mode", ["Sample walkthrough", "Connected model"])
        st.caption("Explore a sample, or analyze your own opportunity with a connected model.")
    st.markdown('<div class="workspace"><strong>Your freelance workspace</strong>One opportunity at a time.</div>', unsafe_allow_html=True)

if page == "My profile":
    render_profile()
    st.stop()

st.markdown('<div class="topline"><span>WORKSPACE &nbsp; / &nbsp; JOB ANALYSIS</span><span class="pill">FIRST LOOK · LOCAL PREVIEW</span></div>', unsafe_allow_html=True)
st.title("Find clarity before you apply.")
st.markdown('<p class="intro">Turn a job description into clear requirements, useful context, and the right questions to ask next.</p>'
            '<div class="steps"><strong>01 &nbsp; Add opportunity</strong><span>—</span>02 &nbsp; Analyze requirements<span>—</span>03 &nbsp; Review insights</div>', unsafe_allow_html=True)

if mode == "Sample walkthrough":
    st.markdown('<div class="demo-note"><strong>You’re exploring a sample.</strong> This walkthrough uses a fixed job and predefined results. No AI model is called.</div>', unsafe_allow_html=True)

include_match = False
if mode == "Connected model":
    include_match = st.checkbox("Include evidence-based profile matching", value=False)
    if include_match:
        selected_profile = st.selectbox("Match against", ["My real profile", "Synthetic demo"])
        workspace = "demo" if selected_profile == "Synthetic demo" else "personal"
        st.caption("Build the selected profile's evidence index in My profile first. Retrieved source excerpts are sent to the configured model for matching.")

entry, guide = st.columns([1.8, 1], gap="large")
with entry:
    with st.container(border=True):
        st.subheader("The opportunity")
        st.caption("Start with the full description. Details make the analysis more useful.")
        if mode == "Sample walkthrough":
            job = SAMPLE_JOB
            st.text_area("Sample job description", value=job, height=230, disabled=True)
        else:
            job = st.text_area("Job description", height=230, max_chars=20000,
                               placeholder="Paste the job description, requested skills, deliverables, budget, and timeline…")
            st.caption("Your description is sent to the model service configured by the app owner.")
        analyze_clicked = st.button("Analyze job", type="primary", use_container_width=True)
        st.caption("Check requirements and source quotes before making a decision.")
with guide:
    st.markdown('<div class="guide"><div class="eyebrow" style="margin-top:0">A clearer starting point</div>'
                '<h3>Know what the job really needs.</h3><p>A focused breakdown to help you decide your next step.</p>'
                '<div class="guide-item"><span class="guide-num">1</span><div><strong>Separate fact from inference</strong>See what the client asked for and what may need clarification.</div></div>'
                '<div class="guide-item"><span class="guide-num">2</span><div><strong>Trace every requirement</strong>Review the original wording behind each extracted requirement.</div></div>'
                '<div class="guide-item"><span class="guide-num">3</span><div><strong>Ask better questions</strong>Spot missing scope, delivery details, and acceptance criteria.</div></div></div>', unsafe_allow_html=True)

if analyze_clicked:
    st.session_state.pop("analysis_result", None)
    try:
        if mode == "Sample walkthrough":
            model_call = lambda job, feedback: json.dumps(SAMPLE_ANALYSIS)
        else:
            settings = Settings(
                provider=setting("LLM_PROVIDER", "compatible_api"),
                base_url=setting("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
                model=setting("LLM_MODEL", "openai/gpt-oss-20b"),
                api_key=setting("LLM_API_KEY"),
            )
            model_call = partial(generate, settings)
        started = time.perf_counter()
        with st.spinner("Analyzing requirements and checking evidence…"):
            if include_match:
                _, profile_revision = load_profile(workspace)
                graph = build_graph(model_call,
                    retrieve=lambda analysis: retrieve(workspace,analysis,profile_revision),
                    match=lambda analysis,evidence: match_requirements(settings,analysis,evidence))
            else:
                graph = build_graph(model_call)
            result = graph.invoke({"job_text": job})
        if result["error"]:
            st.error(result["error"] + " Try another model or revise the job text.")
        else:
            st.session_state.analysis_result = {
                "result": result, "job": job, "mode": mode,
                "seconds": round(time.perf_counter() - started, 2),
            }
            if include_match:
                run_id = persist_match(workspace,job,result,profile_revision)
                st.session_state.analysis_result.update(workspace=workspace,profile_revision=profile_revision,run_id=run_id)
    except (ValueError, ProviderError,OSError) as exc:
        st.session_state.pop("analysis_result",None)
        st.error(str(exc))

saved = st.session_state.get("analysis_result")
same_match_selection = bool(saved) and (("matching" in saved["result"]) == include_match) and (not include_match or saved.get("workspace") == workspace)
if saved and saved["job"] == job and saved["mode"] == mode and same_match_selection:
    result = saved["result"]
    analysis = result["analysis"]
    st.divider()
    st.markdown('<div class="eyebrow">Your opportunity brief</div>', unsafe_allow_html=True)
    st.subheader(analysis["title"])
    st.write(analysis["summary"])
    cols = st.columns(3)
    cols[0].metric("Budget stated", analysis["budget"] or "Not specified")
    cols[1].metric("Timeline stated", analysis["deadline"] or "Not specified")
    cols[2].metric("Analysis attempts", result["attempts"])
    count_explicit = sum(r["kind"] == "explicit" for r in analysis["requirements"])
    count_inferred = len(analysis["requirements"]) - count_explicit
    explicit, inferred, questions = st.tabs([f"Explicit requirements · {count_explicit}", f"Inferred suggestions · {count_inferred}", "Tasks & questions"])
    for tab, kind in [(explicit, "explicit"), (inferred, "inferred")]:
        with tab:
            items = [r for r in analysis["requirements"] if r["kind"] == kind]
            if not items:
                st.write("None identified.")
            for requirement in items:
                evidence_card(requirement["description"], requirement["evidence_quote"])
    with questions:
        st.subheader("Requested tasks")
        for task in analysis["tasks"]:
            st.write("• " + task)
        st.subheader("Questions to clarify")
        for question in analysis["missing_information"]:
            st.write("• " + question)
    st.caption(f"Completed in {saved['seconds']}s. Source quotes are checked automatically; review their meaning yourself.")
    st.download_button("Download analysis JSON", json.dumps(analysis, indent=2),
                       file_name="job-analysis.json", mime="application/json")
    render_match(saved)
else:
    st.markdown('<div class="empty"><div class="empty-icon">◎</div><strong>Your opportunity brief will appear here</strong>'
                '<p>Analyze the description to explore requirements, evidence, and open questions.</p></div>', unsafe_allow_html=True)

st.markdown('<div class="footer">FREELANCE AI &nbsp; · &nbsp; Built for thoughtful applications. &nbsp; Your judgment stays in control.</div>', unsafe_allow_html=True)
