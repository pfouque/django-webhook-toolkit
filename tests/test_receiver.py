from __future__ import annotations

import json
import time
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from tests.testapp.models import AcmeWebhookEvent
from webhook_toolkit.choices import WebhookEventStatus
from webhook_toolkit.signature_mechanisms import get_signature_mechanism


class ReceiverTestCase(TestCase):
    def test_receiver_happy_path(self) -> None:
        assert AcmeWebhookEvent.objects.count() == 0

        payload = {"event": "ping", "id": "evt_123"}
        body = json.dumps(payload).encode("utf-8")
        webhook_id = "evt_test_0"
        timestamp = int(time.time())
        mechanism = get_signature_mechanism("standardwebhooks")
        signature_headers = mechanism.sign_headers(
            payload=body,
            webhook_id=webhook_id,
            timestamp=timestamp,
            secrets=["whsec_dGVzdHNlY3JldA=="],
        )

        response = self.client.post(
            reverse("acme-webhook"),  # "/webhooks/acme/",
            data=body,
            content_type="application/json",
            REMOTE_ADDR="203.0.113.10",
            headers=signature_headers,
        )

        assert response.status_code == HTTPStatus.OK

        event = AcmeWebhookEvent.objects.get()
        assert event.status == WebhookEventStatus.DONE
        assert event.payload == payload
        assert event.remote_ip == "203.0.113.10"
        assert event.headers.get("Content-Type") == "application/json"

    def test_receiver_verifies_signature(self) -> None:
        payload = {"event": "ping", "id": "evt_123"}
        body = json.dumps(payload).encode("utf-8")
        webhook_id = "evt_test_1"
        timestamp = int(time.time())
        mechanism = get_signature_mechanism("standardwebhooks")
        signature_headers = mechanism.sign_headers(
            payload=body,
            webhook_id=webhook_id,
            timestamp=timestamp,
            secrets=["whsec_dGVzdHNlY3JldA=="],
        )

        response = self.client.post(
            reverse("acme-webhook"),
            data=body,
            content_type="application/json",
            headers=signature_headers,
        )

        assert response.status_code == HTTPStatus.OK
        event = AcmeWebhookEvent.objects.get()
        assert event.status == WebhookEventStatus.DONE
        assert event.webhook_id == webhook_id
