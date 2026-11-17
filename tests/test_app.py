import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
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
