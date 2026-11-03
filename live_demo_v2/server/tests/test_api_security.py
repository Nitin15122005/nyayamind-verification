"""Regression tests for the local live-demo API security boundary.

Run from the repository root:
    python -m unittest discover -s live_demo_v2/server/tests -v

The handler is exercised over a real loopback HTTP socket. Pipeline state is
intentionally left uninitialised, so valid requests stop at the normal 503
startup guard and never load models or run inference.
"""

from __future__ import annotations

import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from live_demo_v2.server import app


class ApiSecurityTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        self.port = self.server.server_address[1]
        self.previous_hosts = app.ALLOWED_HOSTS
        app.ALLOWED_HOSTS = {
            f"127.0.0.1:{self.port}",
            f"localhost:{self.port}",
        }
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        app.ALLOWED_HOSTS = self.previous_hosts

    def request(self, method="POST", path="/api/run", payload=None, headers=None, raw_body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        request_headers = dict(headers or {})
        body = raw_body
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        elif raw_body is not None:
            request_headers.setdefault("Content-Type", "application/json")
        if body is not None and "Content-Length" not in request_headers:
            request_headers["Content-Length"] = str(len(body))
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        connection.close()
        return result

    def allowed_headers(self, **extra):
        return {"Origin": "http://localhost:5174", **extra}

    def test_post_rejects_missing_origin(self):
        status, _, body = self.request(payload={"mode": "custom", "text": "test"})
        self.assertEqual(status, 403)
        self.assertIn(b"Origin", body)

    def test_post_rejects_untrusted_origin(self):
        status, _, _ = self.request(
            payload={"mode": "custom", "text": "test"},
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(status, 403)

    def test_post_rejects_non_object_json(self):
        status, _, _ = self.request(payload=["custom", "text"], headers=self.allowed_headers())
        self.assertEqual(status, 400)

    def test_post_rejects_invalid_json(self):
        status, _, _ = self.request(
            headers=self.allowed_headers(),
            raw_body=b'{"mode":',
        )
        self.assertEqual(status, 400)

    def test_post_rejects_duplicate_json_keys(self):
        status, _, _ = self.request(
            headers=self.allowed_headers(),
            raw_body=b'{"mode":"custom","mode":"example","id":"x"}',
        )
        self.assertEqual(status, 400)

    def test_post_rejects_invalid_mode(self):
        status, _, _ = self.request(
            payload={"mode": "other"},
            headers=self.allowed_headers(),
        )
        self.assertEqual(status, 400)

    def test_post_rejects_wrong_custom_text_type(self):
        status, _, _ = self.request(
            payload={"mode": "custom", "text": 123},
            headers=self.allowed_headers(),
        )
        self.assertEqual(status, 400)

    def test_post_rejects_empty_custom_text(self):
        status, _, _ = self.request(
            payload={"mode": "custom", "text": "  \n"},
            headers=self.allowed_headers(),
        )
        self.assertEqual(status, 400)

    def test_post_rejects_extra_fields(self):
        status, _, _ = self.request(
            payload={"mode": "custom", "text": "test", "admin": True},
            headers=self.allowed_headers(),
        )
        self.assertEqual(status, 400)

    def test_post_rejects_unknown_example(self):
        status, _, _ = self.request(
            payload={"mode": "example", "id": "not-a-real-example"},
            headers=self.allowed_headers(),
        )
        self.assertEqual(status, 404)

    def test_post_rejects_non_json_content_type(self):
        status, _, _ = self.request(
            headers={**self.allowed_headers(), "Content-Type": "text/plain"},
            raw_body=b'{"mode":"custom","text":"test"}',
        )
        self.assertEqual(status, 415)

    def test_post_rejects_body_over_one_mib_before_reading_it(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.putrequest("POST", "/api/run")
        connection.putheader("Origin", "http://localhost:5174")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", str(app.MAX_REQUEST_BODY_BYTES + 1))
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 413)
        response.read()
        connection.close()

    def test_post_rejects_custom_text_over_character_limit(self):
        status, _, _ = self.request(
            payload={"mode": "custom", "text": "x" * (app.MAX_CUSTOM_TEXT_CHARS + 1)},
            headers=self.allowed_headers(),
        )
        self.assertEqual(status, 413)

    def test_valid_payload_reaches_startup_guard(self):
        status, _, body = self.request(
            payload={"mode": "custom", "text": "Section 302 IPC"},
            headers=self.allowed_headers(),
        )
        self.assertEqual(status, 503)
        self.assertIn(b"starting up", body)

    def test_allowed_preflight_returns_exact_origin(self):
        status, headers, _ = self.request(
            method="OPTIONS",
            headers={
                "Origin": "http://localhost:5174",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "http://localhost:5174")
        self.assertEqual(headers.get("Vary"), "Origin")

    def test_preflight_rejects_untrusted_origin(self):
        status, _, _ = self.request(
            method="OPTIONS",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertEqual(status, 403)

    def test_preflight_rejects_unapproved_headers(self):
        status, _, _ = self.request(
            method="OPTIONS",
            headers={
                "Origin": "http://localhost:5174",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(status, 403)

    def test_get_does_not_grant_cors_to_untrusted_origin(self):
        status, headers, _ = self.request(
            method="GET",
            path="/api/health",
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(status, 200)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_rejects_untrusted_host_header(self):
        status, _, _ = self.request(
            method="GET",
            path="/api/health",
            headers={"Host": "attacker.example"},
        )
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
