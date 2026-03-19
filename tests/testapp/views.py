from __future__ import annotations

from tests.testapp.models import AcmeWebhookEvent
from webhook_toolkit.receiver.views import WebhookReceiverView


class AcmeWebhookReceiverView(WebhookReceiverView):
    webhook_event_model = AcmeWebhookEvent
    signature_mechanism = "standardwebhooks"
