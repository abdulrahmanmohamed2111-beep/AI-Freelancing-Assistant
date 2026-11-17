import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from assistant_core.profile import Profile, Project, demo_profile, load_profile, save_profile


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.patch = patch.dict(os.environ, {"FREELANCE_DATA_DIR": self.directory.name})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.directory.cleanup()

    def test_demo_never_populates_personal_profile(self):
        demo = demo_profile()
        save_profile("demo", demo, 0)
        self.assertEqual(len(load_profile("demo")[0].projects), 3)
        self.assertEqual(load_profile("personal")[1], 0)
        self.assertEqual(load_profile("personal")[0].projects, [])

    def test_persistence_and_project_ids(self):
        p = Profile(display_name="Test", projects=[Project(title="API", description="Built an API with source documentation.")])
        save_profile("personal", p, 0)
        restored, revision = load_profile("personal")
        self.assertEqual(restored, p)
        self.assertEqual(revision, 1)

    def test_stale_writer_cannot_overwrite(self):
        save_profile("personal", Profile(display_name="First"), 0)
        with self.assertRaisesRegex(ValueError, "another session"):
            save_profile("personal", Profile(display_name="Stale"), 0)
        self.assertEqual(load_profile("personal")[0].display_name, "First")

    def test_invalid_edit_keeps_previous_data(self):
        p = Profile(display_name="Test")
        save_profile("personal", p, 0)
        p.hourly_rate_usd = -20
        with self.assertRaises(ValueError):
            save_profile("personal", p, 1)
        self.assertEqual(load_profile("personal")[1], 1)


if __name__ == "__main__":
    unittest.main()
