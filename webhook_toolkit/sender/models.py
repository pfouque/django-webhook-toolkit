from __future__ import annotations

import datetime as dt
import json
import time
import uuid

import httpx
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db import models
from django.db import transaction
from django.utils import timezone

from webhook_toolkit.choices import WebhookEventStatus
from webhook_toolkit.choices import WebhookSubscriptionStatus
from webhook_toolkit.conf import app_settings
from webhook_toolkit.signature_mechanisms import get_signature_mechanism


class WebhookSubscription(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    description = models.CharField(max_length=254)
    endpoint_url = models.URLField()

    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    status = models.CharField(
        choices=WebhookSubscriptionStatus.choices,
        default=WebhookSubscriptionStatus.ACTIVE,
        max_length=10,
    )

    signing_secrets = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional list of signing secrets used to sign outgoing webhooks.",
    )

    signature_mechanism = models.CharField(
        max_length=64,
        default="standardwebhooks",
        help_text="Signature mechanism used to sign outgoing webhooks.",
    )

    objects = models.Manager()

    def get_signing_secrets(self) -> list[str]:
        """Return signing secrets for this subscription."""
        return list(self.signing_secrets or [])


class WebhookEvent(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    subscription = models.ForeignKey(WebhookSubscription, on_delete=models.CASCADE)
    status = models.CharField(
        choices=WebhookEventStatus.choices,
        default=WebhookEventStatus.PENDING,
        max_length=10,
    )
    retry_count = models.IntegerField(default=0)
    retry_after = models.DateTimeField(default=timezone.now)

    payload = models.JSONField(default=dict, encoder=DjangoJSONEncoder)

    objects = models.Manager()

    webhookeventlog_set: models.QuerySet[WebhookEventLog]

    def execute(self) -> None:
        """Access this instance as ``my_app.conf.app_settings``."""

        res: httpx.Response | None = None
        error: Exception | None = None

        try:
            body = json.dumps(self.payload, separators=(",", ":"), cls=DjangoJSONEncoder)
            body_bytes = body.encode("utf-8")

            headers = {"Content-Type": "application/json"}
            secrets = self.subscription.get_signing_secrets()

            mechanism = get_signature_mechanism(self.subscription.signature_mechanism)

            if secrets:
                webhook_id = str(self.uuid)
                timestamp = int(time.time())
                headers.update(
                    mechanism.sign_headers(
                        payload=body_bytes,
                        webhook_id=webhook_id,
                        timestamp=timestamp,
                        secrets=secrets,
                    )
                )

            res = httpx.post(self.subscription.endpoint_url, content=body_bytes, headers=headers)
            res.raise_for_status()
        except httpx.HTTPError as exc:
            error = exc
            if self.retry_count == app_settings.WEBHOOKS_SENDER_MAX_RETRY:
                self.status = WebhookEventStatus.ABORTED
            else:
                self.update_retry()
        else:
            self.status = WebhookEventStatus.DONE
        finally:
            self.webhookeventlog_set.create(
                webhook_event=self,
                response_status_code=res.status_code if res else 0,
                retry_number=self.retry_count,
                response=res.text if res else str(error or ""),
            )
            self.save()

    def update_retry(self) -> None:
        self.retry_count += 1
        self.retry_after = timezone.now() + dt.timedelta(minutes=2 ** (self.retry_count + 1))

    def reset_for_retry(self) -> None:
        self.status = WebhookEventStatus.PENDING
        self.retry_count = 0
        self.retry_after = timezone.now()
        self.save()

    @classmethod
    def fire(cls) -> None:
        """Access this instance as ``my_app.conf.app_settings``."""

        qs = cls.objects.select_related("subscription").filter(
            subscription__status=WebhookSubscriptionStatus.ACTIVE,
            status=WebhookEventStatus.PENDING,
            retry_after__lte=timezone.now(),
        )

        if connection.features.has_select_for_update:
            qs = qs.select_for_update(
                skip_locked=connection.features.has_select_for_update_skip_locked
            )

        with transaction.atomic():
            for webhook_event in qs:
                webhook_event.execute()


class WebhookEventLog(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    webhook_event = models.ForeignKey(
        WebhookEvent, on_delete=models.CASCADE, related_name="event_logs"
    )
    response_status_code = models.PositiveIntegerField()
    retry_number = models.PositiveIntegerField(default=0)
    response = models.TextField(max_length=4096)

    objects = models.Manager()
