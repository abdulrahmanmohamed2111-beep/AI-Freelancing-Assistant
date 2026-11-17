import copy
import json
import unittest
from unittest.mock import patch

import httpx

from assistant_core.providers import ProviderError, Settings, generate
from assistant_core.sample import SAMPLE_ANALYSIS, SAMPLE_JOB
from assistant_core.workflow import build_graph


class WorkflowTests(unittest.TestCase):
    def test_sample_succeeds(self):
        result = build_graph(lambda *_: json.dumps(SAMPLE_ANALYSIS)).invoke({"job_text": SAMPLE_JOB})
        self.assertEqual(result["analysis"]["budget"], "$500")
        self.assertEqual(result["attempts"], 1)

    def test_retries_invalid_json_once(self):
        answers = iter(["not json", json.dumps(SAMPLE_ANALYSIS)])
        result = build_graph(lambda *_: next(answers)).invoke({"job_text": SAMPLE_JOB})
        self.assertEqual(result["attempts"], 2)
        self.assertFalse(result["error"])

    def test_fabricated_quote_is_rejected_and_retry_is_bounded(self):
        bad = copy.deepcopy(SAMPLE_ANALYSIS)
        bad["requirements"][0]["evidence_quote"] = "Ten years of experience required"
        result = build_graph(lambda *_: json.dumps(bad)).invoke({"job_text": SAMPLE_JOB})
        self.assertEqual(result["attempts"], 2)
        self.assertTrue(result["error"])
        self.assertEqual(result["analysis"], {})

    def test_invalid_input_never_calls_model(self):
        def forbidden(*_):
            self.fail("Model must not run on invalid input")
        for job in ["", " " * 40, "x" * 20001]:
            with self.assertRaises(ValueError):
                build_graph(forbidden).invoke({"job_text": job})

    @patch("assistant_core.providers.httpx.post")
    def test_ollama_schema_and_response(self, post):
        post.return_value = httpx.Response(200, request=httpx.Request("POST", "http://localhost"),
                                         json={"message": {"content": json.dumps(SAMPLE_ANALYSIS)}})
        output = generate(Settings("ollama", "http://localhost:11434", "test-model"), SAMPLE_JOB)
        self.assertEqual(json.loads(output), SAMPLE_ANALYSIS)
        self.assertIn("properties", post.call_args.kwargs["json"]["format"])

    @patch("assistant_core.providers.httpx.post")
    def test_api_response(self, post):
        post.return_value = httpx.Response(200, request=httpx.Request("POST", "https://example.com"),
                                         json={"choices": [{"message": {"content": "{}"}}]})
        self.assertEqual(generate(Settings("compatible_api", "https://example.com/v1", "model", "secret"), SAMPLE_JOB), "{}")
        self.assertEqual(post.call_args.args[0], "https://example.com/v1/chat/completions")

    @patch("assistant_core.providers.httpx.post")
    def test_missing_key_never_sends_request(self, post):
        with self.assertRaisesRegex(ProviderError, "API key"):
            generate(Settings("compatible_api", "https://api.groq.com/openai/v1", "model"), SAMPLE_JOB)
        post.assert_not_called()

    @patch("assistant_core.providers.httpx.post")
    def test_quota_error_is_actionable_and_redacted(self, post):
        post.return_value = httpx.Response(429, request=httpx.Request("POST", "https://example.com"),
                                         text="sensitive provider response")
        with self.assertRaisesRegex(ProviderError, "usage limit") as caught:
            generate(Settings("compatible_api", "https://example.com/v1", "model", "secret"), SAMPLE_JOB)
        self.assertNotIn("sensitive", str(caught.exception))

    @patch("assistant_core.providers.httpx.post")
    def test_timeout_is_safe(self, post):
        post.side_effect = httpx.TimeoutException("sensitive detail")
        with self.assertRaisesRegex(ProviderError, "timed out"):
            generate(Settings("ollama", "http://localhost:11434", "test"), SAMPLE_JOB)


if __name__ == "__main__":
    unittest.main()
