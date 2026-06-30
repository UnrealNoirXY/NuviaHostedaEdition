import json

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from hr_portal.middleware import StructuredLogMiddleware
from hr_portal.observability import emit_structured_log, metrics


class StructuredLogMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_logs_request_metadata(self):
        middleware = StructuredLogMiddleware(lambda request: HttpResponse("ok"))
        request = self.factory.get("/observability-check")

        with self.assertLogs("hr_portal.observability", level="INFO") as captured:
            response = middleware(request)

        self.assertEqual(response.status_code, 200)
        logged = "".join(captured.output)
        self.assertIn("http_request", logged)
        _, histograms = metrics.snapshot()
        self.assertTrue(any(name == "http_request_duration_ms" for name, _ in histograms.keys()))


class StructuredLogHelperTests(SimpleTestCase):
    def test_emit_structured_log_serializes_payload(self):
        sample = {"hello": "world"}
        with self.assertLogs("hr_portal.observability", level="INFO") as captured:
            emit_structured_log("test_event", payload=sample)

        self.assertTrue(captured.output)
        parsed = json.loads(captured.output[0].split(":", 2)[-1])
        self.assertEqual(parsed.get("event"), "test_event")
        self.assertEqual(parsed.get("payload"), sample)
