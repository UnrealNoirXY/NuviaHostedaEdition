from django.test import SimpleTestCase
from django.urls import resolve


class PreviewStreamRouteTests(SimpleTestCase):
    def test_preview_stream_batch_route_points_to_dedicated_action(self):
        match = resolve('/api/hr/payslip-batches/00000000-0000-0000-0000-000000000000/preview-stream/')
        self.assertEqual(match.func.actions.get('get'), 'preview_stream_batch')

    def test_preview_stream_job_route_points_to_dedicated_action(self):
        match = resolve('/api/hr/payslip-batches/preview-stream/00000000-0000-0000-0000-000000000000/')
        self.assertEqual(match.func.actions.get('get'), 'preview_stream_job')
