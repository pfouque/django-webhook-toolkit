from __future__ import annotations

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("webhook_toolkit_sender", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="webhooksubscription",
            name="signing_secrets",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Optional list of signing secrets used to sign outgoing webhooks.",
            ),
        ),
    ]
