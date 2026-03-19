from __future__ import annotations

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("webhook_toolkit_sender", "0002_subscription_signing_secrets"),
    ]

    operations = [
        migrations.AddField(
            model_name="webhooksubscription",
            name="signature_mechanism",
            field=models.CharField(
                default="standardwebhooks",
                help_text="Signature mechanism used to sign outgoing webhooks.",
                max_length=64,
            ),
        ),
    ]
