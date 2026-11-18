from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from assistant_core.cv import CVExtraction, CVProject, apply_cv, extract_cv, read_cv, redact_contacts
from assistant_core.profile import Profile, connect, load_profile, save_profile

TEXT = (Path(__file__).resolve().parents[1] / "fixtures/synthetic/demo_cv.txt").read_text()


def draft():
    return CVExtraction(display_name="Demo Freelancer", headline="Python Developer", summary="Personal learning projects.",
        skills=["Python"], education="", experience="", projects=[CVProject(title="Inventory REST API",
        description="Built an inventory REST API using Python and FastAPI.", role="Developer", technologies=["Python"],
        source_quote="Built an inventory REST API using Python and FastAPI")])


class CVTests(unittest.TestCase):
    def test_whitespace_quote_restores_original_span(self):
        changed = TEXT.replace("Python and FastAPI", "Python\n and\u00a0FastAPI")
        with patch("assistant_core.cv.generate", return_value=draft().model_dump_json()):
            result = extract_cv(None, changed)
        self.assertIn(result.projects[0].source_quote, changed)

    def test_invalid_schema_repaired_once(self):
        with patch("assistant_core.cv.generate", side_effect=["invalid", draft().model_dump_json()]) as generate:
            result = extract_cv(None, TEXT)
        self.assertEqual(result.display_name, "Demo Freelancer")
        self.assertEqual(generate.call_count, 2)
        self.assertIn("Schema errors", generate.call_args.args[2])

    def test_unsupported_quote_is_retried_and_never_accepted(self):
        bad = draft(); bad.projects[0].source_quote = "Invented cloud deployment"
        with patch("assistant_core.cv.generate", return_value=bad.model_dump_json()) as generate:
            with self.assertRaisesRegex(ValueError, "traceable source quotes"):
                extract_cv(None, TEXT)
        self.assertEqual(generate.call_count, 2)

    def test_txt_and_invalid_inputs(self):
        self.assertIn("Inventory", read_cv("cv.txt", TEXT.encode()))
        for name, content in [("cv.pdf", b"not PDF"), ("cv.txt", b"short"), ("cv.docx", b"x"*100), ("cv.txt", b"x"*(5*1024*1024+1))]:
            with self.assertRaises(ValueError):
                read_cv(name, content)

    def test_pdf_text_and_scanned_page(self):
        writer = PdfWriter()
        page = writer.add_blank_page(width=600, height=800)
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 30 750 Td (Demo CV: Python developer with FastAPI and PostgreSQL experience. Built an inventory API and wrote automated tests.) Tj ET")
        font = DictionaryObject({NameObject('/Type'):NameObject('/Font'), NameObject('/Subtype'):NameObject('/Type1'), NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'):font})})
        page[NameObject('/Contents')] = writer._add_object(stream)
        output = BytesIO(); writer.write(output)
        self.assertIn("FastAPI", read_cv("cv.pdf", output.getvalue()))
        writer = PdfWriter(); writer.add_blank_page(width=600, height=800)
        output = BytesIO(); writer.write(output)
        with self.assertRaisesRegex(ValueError, "OCR"):
            read_cv("scan.pdf", output.getvalue())

    def test_contacts_and_quote_validation(self):
        cleaned = redact_contacts("Email a@example.com phone +20 100 123 4567")
        self.assertNotIn("a@example.com", cleaned)
        self.assertNotIn("123 4567", cleaned)
        with patch("assistant_core.cv.generate", return_value=draft().model_dump_json()):
            self.assertEqual(extract_cv(None, TEXT).display_name, "Demo Freelancer")
        bad = draft(); bad.projects[0].source_quote = "Unstated AWS expertise"
        with patch("assistant_core.cv.generate", return_value=bad.model_dump_json()), self.assertRaises(ValueError):
            extract_cv(None, TEXT)

    def test_reimport_is_idempotent_and_preserves_availability(self):
        original = Profile(display_name="Old", availability_hours_per_week=12, education="Existing education")
        imported = apply_cv(original, draft(), TEXT)
        again = apply_cv(imported, draft(), TEXT)
        self.assertEqual(len(again.projects), 1)
        self.assertEqual(again.availability_hours_per_week, 12)
        self.assertEqual(again.education, "Existing education")
        self.assertEqual(original.projects, [])
        self.assertTrue(again.projects[0].source_id)

    def test_legacy_rate_is_removed_and_save_still_works(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"FREELANCE_DATA_DIR": directory}):
            with connect() as db:
                db.execute("INSERT INTO profiles VALUES (?, ?, ?)", ("personal", json.dumps({"display_name":"Old", "hourly_rate_usd":25}), 1))
            profile, revision = load_profile("personal")
            self.assertNotIn("hourly_rate_usd", profile.model_dump())
            save_profile("personal", profile, revision)
            with connect() as db:
                self.assertNotIn("hourly_rate_usd", db.execute("SELECT payload FROM profiles").fetchone()[0])


class CVUITests(unittest.TestCase):
    def test_upload_review_requires_approval_before_save(self):
        from streamlit.testing.v1 import AppTest
        upload = BytesIO(TEXT.encode()); upload.name = "synthetic.txt"
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"FREELANCE_DATA_DIR": directory}), \
             patch("streamlit.file_uploader", return_value=upload), patch("cv_page.extract_cv", return_value=draft()):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py")).run()
            app.selectbox(key="workspace_page").set_value("My profile").run()
            next(b for b in app.button if b.label == "Extract profile").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(load_profile("personal")[1], 0)
            next(b for b in app.button if b.label == "Approve and save profile").click().run()
            self.assertTrue(app.error)
            self.assertEqual(load_profile("personal")[1], 0)
            next(c for c in app.checkbox if c.label.startswith("I reviewed these details")).check()
            next(b for b in app.button if b.label == "Approve and save profile").click().run()
            self.assertFalse(app.exception)
            saved, revision = load_profile("personal")
            self.assertEqual(revision, 1)
            self.assertEqual(saved.display_name, "Demo Freelancer")
            self.assertEqual(len(saved.projects), 1)
            self.assertFalse(any("rate" in n.label.lower() for n in app.number_input))
