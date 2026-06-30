from django.db import migrations
from django.utils import timezone


DEFAULT_POLICY_CONTENT = """
<h2>Informativa Privacy</h2>
<p>
    Questa informativa descrive come vengono raccolti e utilizzati i dati personali
    per l'accesso alla piattaforma e ai servizi associati.
</p>
<ul>
    <li>Finalita: gestione dell'account e del rapporto di lavoro.</li>
    <li>Base giuridica: adempimento di obblighi contrattuali e normativi.</li>
    <li>Conservazione: per il tempo necessario alle finalita sopra descritte.</li>
</ul>
<p>
    Per ulteriori dettagli o richieste di esercizio dei diritti, contatta l'assistenza.
</p>
""".strip()


def create_default_privacy_policy(apps, schema_editor):
    PrivacyPolicyVersion = apps.get_model("accounts", "PrivacyPolicyVersion")
    if PrivacyPolicyVersion.objects.filter(is_active=True).exists():
        return

    now = timezone.now()
    policy, created = PrivacyPolicyVersion.objects.get_or_create(
        version="v1.0",
        defaults={
            "content": DEFAULT_POLICY_CONTENT,
            "published_at": now,
            "is_active": True,
        },
    )

    if not created:
        updated = False
        if not policy.content:
            policy.content = DEFAULT_POLICY_CONTENT
            updated = True
        if not policy.published_at:
            policy.published_at = now
            updated = True
        if not policy.is_active:
            policy.is_active = True
            updated = True
        if updated:
            policy.save()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0029_user_must_change_password"),
    ]

    operations = [
        migrations.RunPython(create_default_privacy_policy, migrations.RunPython.noop),
    ]
