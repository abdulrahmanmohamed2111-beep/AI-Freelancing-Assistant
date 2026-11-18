import streamlit as st
from assistant_core.database import database_url
from assistant_core.profile import load_profile
from assistant_core.rag import build_index,index_status
from assistant_core.schemas import capability_requirements


def render_index(workspace):
    st.subheader("Evidence index")
    st.caption("Index approved CV text and reviewed projects for job matching. English sources are supported in this first version. Embeddings run locally on CPU.")
    if not database_url():
        st.info("Set up PostgreSQL before building an evidence index.")
        return
    try:
        _, revision = load_profile(workspace)
        status = index_status(workspace)
        if status:
            st.write(f"{status[2]} chunks · profile version {status[0]}")
            if status[0] != revision:
                st.warning("Your profile has changed. Rebuild the index before matching.")
            else:
                st.success("Evidence index is up to date.")
        else:
            st.info("No evidence index yet. Approve your CV or review a project, then build it.")
        if st.button("Build / refresh evidence index", key=f"index_{workspace}"):
            with st.spinner("Building source chunks and local embeddings… First use downloads a small model."):
                result = build_index(workspace)
            st.success(f"Indexed {result['documents']} documents into {result['chunks']} chunks.")
    except (OSError,ValueError) as exc:
        st.error(str(exc))


def render_match(saved):
    result = saved["result"]
    if "matching" not in result:
        return
    st.divider()
    st.subheader("Your fit, backed by evidence")
    st.caption(f"{'Synthetic demo' if saved['workspace']=='demo' else 'Your profile'} · profile version {saved['profile_revision']} · run {saved['run_id'][:8]}")
    try:
        _, current = load_profile(saved["workspace"])
        if current != saved["profile_revision"]:
            st.warning("This assessment uses an older profile version. Rebuild the index and analyze again.")
    except (OSError,ValueError):
        st.warning("Could not check whether the profile has changed.")
    match = result["matching"]
    st.metric("Evidence coverage", f"{match['score']}%" if match["score"] is not None else "Not assessable")
    st.caption(match["rubric"])
    st.info("Requirement coverage does not guarantee readiness or acceptance. A missing critical requirement may outweigh the overall score. Proposed tools, pricing and delivery estimates come in later stages.")
    sources = {c["chunk_id"]:c for item in result["retrieval"] for c in item["candidates"]}
    requirements = capability_requirements(result["analysis"])
    for item in match["requirements"]:
        with st.expander(f"{item['status'].upper()} · {requirements[item['requirement_index']]['description']}",expanded=True):
            st.write(item["explanation"])
            for gap in item["gaps"]:
                st.write("Gap: "+gap)
            for evidence in item["evidence"]:
                source = sources[evidence["chunk_id"]]
                st.caption(f"{source['metadata']['title']} · chunk {evidence['chunk_id']}")
                st.text(evidence["quote"])
