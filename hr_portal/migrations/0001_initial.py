# Generated manually to bootstrap HR portal models
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0027_user_menu_creation_studio_enabled"),
        ("clients", "0005_structurerole_can_approve_menu_and_more"),
        ("resort", "0006_seed_resorts"),
    ]

    operations = [
        migrations.CreateModel(
            name="HRDocument",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "category",
                    models.CharField(
                        choices=[("notice", "Comunicazione"), ("policy", "Policy"), ("form", "Modulo"), ("other", "Altro")],
                        default="notice",
                        max_length=20,
                    ),
                ),
                ("file", models.FileField(upload_to="hr/documents/")),
                ("audience_roles", models.JSONField(blank=True, default=list, help_text="Ruoli destinatari")),
                ("requires_acknowledgement", models.BooleanField(default=False)),
                ("visible_from", models.DateTimeField(default=django.utils.timezone.now)),
                ("visible_until", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "acknowledged_by",
                    models.ManyToManyField(blank=True, related_name="hr_documents_acknowledged", to="accounts.user"),
                ),
                (
                    "audience_company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hr_documents",
                        to="clients.company",
                    ),
                ),
                (
                    "audience_resort",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hr_documents",
                        to="resort.resort",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="hr_documents_uploaded",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PayslipBatch",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("source_file", models.FileField(upload_to="hr/payslip_batches/")),
                ("status", models.CharField(choices=[("pending", "In attesa"), ("processing", "In elaborazione"), ("completed", "Completato"), ("failed", "Fallito")], db_index=True, default="pending", max_length=20)),
                ("auto_match_strategy", models.CharField(default="username", help_text="Strategia di auto-match: username, email o regex su fiscal_code", max_length=50)),
                ("manifest_hint", models.CharField(blank=True, default="", help_text="Regex per intercettare codice fiscale/ID nel nome file", max_length=255)),
                ("total_items", models.PositiveIntegerField(default=0)),
                ("matched_items", models.PositiveIntegerField(default=0)),
                ("failed_items", models.PositiveIntegerField(default=0)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("processing_log", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "company",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="clients.company"),
                ),
                (
                    "resort",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="resort.resort"),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payslip_batches",
                        to="accounts.user",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ListeningTicket",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                (
                    "priority",
                    models.CharField(
                        choices=[("low", "Bassa"), ("normal", "Normale"), ("high", "Alta")],
                        default="normal",
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("new", "Nuovo"), ("in_progress", "In lavorazione"), ("closed", "Chiuso")],
                        db_index=True,
                        default="new",
                        max_length=20,
                    ),
                ),
                ("subject", models.CharField(max_length=255)),
                ("message", models.TextField()),
                ("is_anonymous", models.BooleanField(default=False)),
                ("sentiment", models.CharField(blank=True, default="", max_length=20)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="listening_tickets_assigned",
                        to="accounts.user",
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="listening_tickets",
                        to="accounts.user",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="clients.company"),
                ),
                (
                    "resort",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="resort.resort"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Payslip",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("period_label", models.CharField(blank=True, default="", max_length=50)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "In attesa"), ("available", "Disponibile"), ("requires_review", "Da revisionare")],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("file", models.FileField(upload_to="hr/payslips/")),
                ("auto_matched", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("downloaded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "batch",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payslips", to="hr_portal.payslipbatch"),
                ),
                (
                    "company",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="clients.company"),
                ),
                (
                    "resort",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="resort.resort"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payslips", to="accounts.user"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="hrdocument",
            index=models.Index(fields=["category", "visible_from"], name="hr_portal_h_category_4388b6_idx"),
        ),
        migrations.AddIndex(
            model_name="hrdocument",
            index=models.Index(fields=["visible_from", "visible_until"], name="hr_portal_h_visible__6c16e2_idx"),
        ),
        migrations.AddIndex(
            model_name="payslip",
            index=models.Index(fields=["status", "created_at"], name="hr_portal_p_status__6b23eb_idx"),
        ),
        migrations.AddIndex(
            model_name="listeningticket",
            index=models.Index(fields=["status", "priority", "created_at"], name="hr_portal_l_status__3e66c8_idx"),
        ),
    ]
