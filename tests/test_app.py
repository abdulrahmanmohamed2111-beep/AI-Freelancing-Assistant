import unittest
import os
import tempfile
from unittest.mock import patch
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
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
