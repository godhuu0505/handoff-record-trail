"""Exercise the local HTTP entry point and compare it with CLI evidence."""

import http.client
import json
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from server import DemoHandler, ThreadingHTTPServer


class DemoHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.expected = json.loads(Path(__file__).with_name("results.json").read_text())["cases"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        try:
            connection.request("GET", path, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def test_steps_match_cli_and_can_be_revisited(self):
        for step in [0, 1, 2, 3, 4, 5, 3, 1, 3]:
            with self.subTest(step=step):
                status, content_type, body = self.get(f"/api/trace?step={step}")
                self.assertEqual(status, 200)
                self.assertIn("application/json", content_type)
                result = json.loads(body)
                self.assertEqual(result["step"], step)
                self.assertEqual(result["trace"], self.expected[step]["trace"])
                self.assertEqual(result["engine"], "Relate 1.0.2")

    def test_bad_steps_are_rejected(self):
        for query in ["", "?step=", "?step=-1", "?step=6", "?step=a", "?step=01", "?step=0&step=1", "?step=0&extra=1"]:
            with self.subTest(query=query):
                self.assertEqual(self.get("/api/trace" + query)[0], 400)

    def test_page_and_unknown_paths(self):
        status, content_type, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn(b"Handoff Record Trail", body)
        self.assertEqual(self.get("/trace.py")[0], 404)
        self.assertEqual(self.get("/results.json")[0], 404)

    def test_foreign_hosts_are_rejected(self):
        self.assertEqual(self.get("/api/trace?step=0", {"Host": "example.test"})[0], 403)

    def test_engine_failure_returns_an_error(self):
        with patch("server.query_step", side_effect=RuntimeError("fixture failure")):
            status, _, body = self.get("/api/trace?step=0")
        self.assertEqual(status, 500)
        self.assertIn("error", json.loads(body))
        self.assertNotIn(b"shared_version_id", body)


if __name__ == "__main__":
    unittest.main()
