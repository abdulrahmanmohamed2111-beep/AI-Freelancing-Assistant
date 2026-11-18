import unittest
import os
import tempfile
from unittest.mock import patch
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_connected_analysis_renders_matching_from_same_graph(self):
        import json
        from assistant_core.sample import SAMPLE_ANALYSIS,SAMPLE_JOB
        from assistant_core.profile import Profile
        # Import UI modules before patching their dependency to avoid retaining
        # a mocked from-import in later tests.
        import profile_page
        import rag_ui
        with patch("assistant_core.providers.generate",return_value=json.dumps(SAMPLE_ANALYSIS)), \
             patch("assistant_core.profile.load_profile",return_value=(Profile(),1)), \
             patch("assistant_core.rag.retrieve",return_value=[]), \
             patch("assistant_core.matching.match_requirements",return_value={"score":0,"rubric":"Test coverage rubric","requirements":[]}), \
             patch("assistant_core.runs.persist_match",return_value="test-run-id"):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run()
            app.radio[0].set_value("Connected model").run()
            next(c for c in app.checkbox if c.label=="Include evidence-based profile matching").check().run()
            app.text_area[0].set_value(SAMPLE_JOB)
            next(b for b in app.button if b.label=="Analyze job").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any(m.label=="Evidence coverage" and m.value=="0%" for m in app.metric))

    def test_profile_demo_save_and_personal_separation(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"FREELANCE_DATA_DIR": directory}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
            app.selectbox(key="workspace_page").set_value("My profile").run()
            self.assertFalse(app.exception)
            app.radio[0].set_value("Synthetic demo").run()
            next(b for b in app.button if b.label == "Load synthetic profile").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[1].value, "3")
            next(t for t in app.text_input if t.label == "Display name").set_value("Edited demo")
            next(b for b in app.button if b.label == "Save profile").click().run()
            self.assertFalse(app.exception)
            app.radio[0].set_value("My real profile").run()
            self.assertEqual(app.metric[1].value, "0")
            self.assertEqual(next(t for t in app.text_input if t.label == "Display name").value, "")

    def test_demo_and_mode_change(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
        self.assertFalse(app.exception)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "$500")
        app.radio[0].set_value("Connected model").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 0)
        app.button[0].click().run()
        self.assertTrue(app.error)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
