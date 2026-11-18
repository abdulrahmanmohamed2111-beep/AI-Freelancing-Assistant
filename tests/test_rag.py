import json
import unittest
from assistant_core.rag import chunks,sources
from assistant_core.profile import Profile,Project
from assistant_core.matching import validate_match
from assistant_core.workflow import build_graph
from assistant_core.sample import SAMPLE_ANALYSIS,SAMPLE_JOB
from assistant_core.schemas import capability_requirements


class RAGTests(unittest.TestCase):
    def test_constraints_excluded_from_experience_score(self):
        analysis = {"requirements":[{"kind":"explicit","category":"capability","description":"Python"},
                                    {"kind":"explicit","category":"constraint","description":"$500 budget"}]}
        self.assertEqual(len(capability_requirements(analysis)),1)

    def test_chunk_spans_preserve_source_and_cover_end(self):
        text = "word\n"*700
        result = list(chunks(text))
        self.assertEqual(result[-1][1],len(text))
        self.assertTrue(all(text[start:end]==span and len(span)<=900 for start,end,span in result))
        self.assertEqual(result[0][1]-result[1][0],150)

    def test_unreviewed_project_excluded(self):
        p = Profile(projects=[Project(title="Unreviewed",description="This is unreviewed source text."),
                              Project(title="Reviewed",description="This is reviewed source text.",reviewed=True)])
        self.assertEqual([s[1] for s in sources(p)],["Reviewed"])

    def test_fabricated_citation_and_missing_coverage_rejected(self):
        retrieval = [{"requirement_index":0,"candidates":[{"chunk_id":"a","content":"Built a Python API."}]}]
        raw = {"requirements":[{"requirement_index":0,"status":"supported","explanation":"Uses Python","gaps":[],"evidence":[{"chunk_id":"a","quote":"Built a Python API."}]}]}
        self.assertEqual(validate_match(json.dumps(raw),retrieval)["score"],100)
        raw["requirements"][0]["evidence"][0]["quote"] = "Used React"
        with self.assertRaises(ValueError):
            validate_match(json.dumps(raw),retrieval)
        raw["requirements"] = []
        with self.assertRaises(ValueError):
            validate_match(json.dumps(raw),retrieval)

    def test_graph_passes_validated_analysis_to_retrieval_and_match(self):
        calls = []
        def retrieve(analysis):
            calls.append("retrieve")
            self.assertEqual(analysis["budget"],"$500")
            return [{"candidate":"source"}]
        def match(analysis,evidence):
            calls.append("match")
            self.assertEqual(evidence,[{"candidate":"source"}])
            return {"score":50}
        result = build_graph(lambda *_:json.dumps(SAMPLE_ANALYSIS),retrieve=retrieve,match=match).invoke({"job_text":SAMPLE_JOB})
        self.assertEqual(calls,["retrieve","match"])
        self.assertEqual(result["matching"]["score"],50)

    def test_invalid_analysis_never_retrieves(self):
        def forbidden(*_):
            self.fail("Invalid analysis must never reach matching")
        result = build_graph(lambda *_:"{}",retrieve=forbidden,match=forbidden).invoke({"job_text":SAMPLE_JOB})
        self.assertTrue(result["error"])
