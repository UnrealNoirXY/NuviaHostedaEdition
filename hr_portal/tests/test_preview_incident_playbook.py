from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from hr_portal.models import HREventLog


class PreviewIncidentPlaybookTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.hr_user = User.objects.create_user(
            username="hr_incident",
            password="pwd",
            role=User.RISORSE_UMANE,
        )
        self.client.force_authenticate(self.hr_user)

    def _seed_alerting_preview_events(self):
        HREventLog.objects.create(
            event_type="preview_started",
            actor=self.hr_user,
            target_model="PayslipPreviewJob",
            target_id="job-1",
            metadata={},
            company=getattr(self.hr_user, "company", None),
            resort=getattr(self.hr_user, "resort", None),
        )
        HREventLog.objects.create(
            event_type="preview_failed",
            actor=self.hr_user,
            target_model="PayslipPreviewJob",
            target_id="job-1",
            metadata={"error": "SSE/proxy timeout"},
            company=getattr(self.hr_user, "company", None),
            resort=getattr(self.hr_user, "resort", None),
        )

    def test_kpi_exposes_incident_playbook_and_state(self):
        self._seed_alerting_preview_events()

        response = self.client.get("/api/hr/kpi/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pipeline = response.data["payslip_preview_pipeline"]
        self.assertTrue(pipeline["incident_open"])
        self.assertIn("incident_state", pipeline)
        self.assertFalse(pipeline["incident_state"]["acknowledged"])
        self.assertGreaterEqual(len(pipeline.get("incident_playbook", [])), 1)
        self.assertIn("command_hint", pipeline.get("incident_playbook", [])[0])
        self.assertIsInstance(pipeline.get("incident_journal", []), list)
        self.assertIn("incident_response_metrics", pipeline)

    def test_incident_ack_endpoint_updates_incident_state(self):
        self._seed_alerting_preview_events()

        ack_response = self.client.post(
            "/api/hr/kpi/incident-ack/",
            {"note": "Worker verificato, monitoro SSE", "alert_level": "critical"},
            format="json",
        )
        self.assertEqual(ack_response.status_code, status.HTTP_201_CREATED)

        response = self.client.get("/api/hr/kpi/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        incident_state = response.data["payslip_preview_pipeline"]["incident_state"]
        self.assertTrue(incident_state["acknowledged"])
        self.assertEqual(incident_state["note"], "Worker verificato, monitoro SSE")
        self.assertEqual(incident_state["acknowledged_by"], self.hr_user.username)

    def test_incident_resolve_endpoint_adds_journal_entry(self):
        self._seed_alerting_preview_events()

        response = self.client.post(
            "/api/hr/kpi/incident-resolve/",
            {
                "resolution_note": "Ripristinato worker e timeout proxy",
                "root_cause": "Configurazione buffering proxy errata",
                "action_items": "Aggiungere check giornaliero SSE\nDocumentare runbook",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        kpi_response = self.client.get("/api/hr/kpi/")
        self.assertEqual(kpi_response.status_code, status.HTTP_200_OK)
        pipeline = kpi_response.data["payslip_preview_pipeline"]
        self.assertTrue(pipeline["incident_state"]["resolved_at"])
        self.assertEqual(pipeline["incident_state"]["root_cause"], "Configurazione buffering proxy errata")
        self.assertGreaterEqual(len(pipeline.get("incident_journal", [])), 1)
        self.assertGreaterEqual(pipeline["incident_response_metrics"]["resolution_rate"], 0)
        self.assertIn("corrective_actions", pipeline)
        self.assertIn("corrective_action_metrics", pipeline)

    def test_incident_action_completion_updates_corrective_metrics(self):
        self._seed_alerting_preview_events()
        self.client.post(
            "/api/hr/kpi/incident-resolve/",
            {
                "resolution_note": "Stabilizzato",
                "root_cause": "Timeout proxy",
                "action_items": "Aggiornare timeout nginx\nAggiungere alert MTTR",
            },
            format="json",
        )

        mark_response = self.client.post(
            "/api/hr/kpi/incident-action-complete/",
            {"action_id": "A1", "label": "Aggiornare timeout nginx"},
            format="json",
        )
        self.assertEqual(mark_response.status_code, status.HTTP_201_CREATED)

        kpi_response = self.client.get("/api/hr/kpi/")
        self.assertEqual(kpi_response.status_code, status.HTTP_200_OK)
        pipeline = kpi_response.data["payslip_preview_pipeline"]
        metrics = pipeline["corrective_action_metrics"]
        self.assertEqual(metrics["total"], 2)
        self.assertEqual(metrics["completed"], 1)
        self.assertEqual(metrics["open"], 1)

    def test_kpi_exposes_phase3_funnel_and_latency_metrics(self):
        self._seed_alerting_preview_events()
        HREventLog.objects.create(
            event_type="preview_confirmed",
            actor=self.hr_user,
            target_model="PayslipBatchPreview",
            target_id="preview-lock-1",
            metadata={"preview_token": "preview-lock-1"},
            company=getattr(self.hr_user, "company", None),
            resort=getattr(self.hr_user, "resort", None),
        )
        HREventLog.objects.create(
            event_type="payslip_batch_created",
            actor=self.hr_user,
            target_model="PayslipBatch",
            target_id="batch-1",
            metadata={"batch_id": "batch-1", "preview_token": "preview-lock-1", "has_preview_token": True},
            company=getattr(self.hr_user, "company", None),
            resort=getattr(self.hr_user, "resort", None),
        )

        response = self.client.get("/api/hr/kpi/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pipeline = response.data["payslip_preview_pipeline"]
        self.assertIn("batch_created", pipeline)
        self.assertIn("preview_to_confirm_rate", pipeline)
        self.assertIn("confirm_to_batch_rate", pipeline)
        self.assertIn("avg_preview_completion_minutes", pipeline)
        self.assertIn("avg_preview_failure_minutes", pipeline)
        self.assertIn("matching_mix", pipeline)
        self.assertIn("funnel", pipeline)
        self.assertIn("targets", pipeline["incident_response_metrics"])
        self.assertIn("breaches", pipeline["incident_response_metrics"])


    def test_kpi_exposes_phase4_operational_metrics(self):
        self._seed_alerting_preview_events()
        HREventLog.objects.create(
            event_type="preview_confirmed",
            actor=self.hr_user,
            target_model="PayslipBatchPreview",
            target_id="preview-lock-2",
            metadata={"preview_token": "preview-lock-2", "has_manual_assignments": True},
            company=getattr(self.hr_user, "company", None),
            resort=getattr(self.hr_user, "resort", None),
        )
        HREventLog.objects.create(
            event_type="payslip_resolved",
            actor=self.hr_user,
            target_model="PayslipUnmatched",
            target_id="unm-1",
            metadata={"source": "manual_resolve"},
            company=getattr(self.hr_user, "company", None),
            resort=getattr(self.hr_user, "resort", None),
        )

        response = self.client.get("/api/hr/kpi/?window_days=14")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pipeline = response.data["payslip_preview_pipeline"]
        self.assertIn("avg_preview_to_confirm_minutes", pipeline)
        self.assertIn("first_pass_resolution_rate", pipeline)
        self.assertIn("manual_assignment_error_reduction_rate", pipeline)
        self.assertIn("manual_assignment_errors_current", pipeline)
        self.assertIn("manual_assignment_errors_previous", pipeline)
        self.assertIn("phase4_summary", pipeline)
        self.assertIn("targets", pipeline["phase4_summary"])
        self.assertIn("status", pipeline["phase4_summary"])
