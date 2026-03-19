from __future__ import annotations

from django.apps import AppConfig


class WebhookToolkitSenderConfig(AppConfig):
    name = "webhook_toolkit.receiver"
    label = "webhook_toolkit_receiver"
    verbose_name = "Webhook Toolkit Receiver"
