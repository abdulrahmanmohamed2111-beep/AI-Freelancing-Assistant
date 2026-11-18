from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from assistant_core.schemas import validate_analysis


class AnalysisState(TypedDict, total=False):
    job_text: str
    raw_output: str
    analysis: dict
    attempts: int
    error: str
    retrieval: list
    matching: dict


def build_graph(generate: Callable[[str, str], str], *, retrieve=None, match=None):
    """A first workflow slice: validate input -> analyze -> verify -> retry once."""
    def prepare(state: AnalysisState):
        job = state.get("job_text", "").strip()
        if not 30 <= len(job) <= 20000:
            raise ValueError("Enter a job description between 30 and 20,000 characters.")
        return {"job_text": job, "attempts": 0, "error": "", "analysis": {}}

    def analyze(state: AnalysisState):
        feedback = ("Your previous result failed schema or quote validation. Return a complete "
                    "JSON object matching the schema and use exact quotes from the job."
                    if state.get("error") else "")
        return {"raw_output": generate(state["job_text"], feedback),
                "attempts": state["attempts"] + 1}

    def verify(state: AnalysisState):
        try:
            analysis = validate_analysis(state["raw_output"], state["job_text"])
            return {"analysis": analysis.model_dump(), "error": ""}
        except ValueError:
            return {"analysis": {}, "error": "The model output failed schema or evidence validation."}

    if (retrieve is None) != (match is None):
        raise ValueError("Retrieval and matching must be configured together.")

    def route(state: AnalysisState):
        if state["error"]:
            return "analyze" if state["attempts"] < 2 else END
        return "retrieve" if retrieve else END

    graph = StateGraph(AnalysisState)
    graph.add_node("prepare", prepare)
    graph.add_node("analyze", analyze)
    graph.add_node("verify", verify)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "analyze")
    graph.add_edge("analyze", "verify")
    routes = {"analyze":"analyze",END:END}
    if retrieve:
        graph.add_node("retrieve", lambda state: {"retrieval":retrieve(state["analysis"])})
        graph.add_node("match", lambda state: {"matching":match(state["analysis"],state["retrieval"])})
        graph.add_edge("retrieve","match")
        graph.add_edge("match",END)
        routes["retrieve"] = "retrieve"
    graph.add_conditional_edges("verify", route, routes)
    return graph.compile()
