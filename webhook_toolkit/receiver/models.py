from __future__ import annotations

import json
import typing
import uuid
from abc import abstractmethod
from traceback import format_exc

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import reverse

from webhook_toolkit.choices import WebhookEventStatus

if typing.TYPE_CHECKING:
    from django.core.handlers.wsgi import WSGIRequest


class _WebhookEvent(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    headers = models.JSONField(default=dict)
    payload = models.JSONField(default=dict, encoder=DjangoJSONEncoder)

    class Meta:
        abstract = True


class AbstractWebhookEvent(_WebhookEvent):
    # NOTE: https://adamj.eu/tech/2021/05/09/how-to-build-a-webhook-receiver-in-django/

    remote_ip = models.GenericIPAddressField(help_text="IP address of the request client.")

    webhook_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        help_text="Unique webhook ID used for idempotency.",
    )

    webhook_timestamp = models.BigIntegerField(
        null=True, blank=True, help_text="Unix timestamp (seconds) from webhook-timestamp."
    )

    status = models.CharField(
        choices=WebhookEventStatus.choices, default=WebhookEventStatus.PENDING, max_length=10
    )

    exception = models.TextField(blank=True)
    traceback = models.TextField(
        blank=True, help_text="Traceback if an exception was thrown during processing"
    )

    objects = models.Manager()

    class Meta:
        abstract = True

    @classmethod
    def create_from_request(cls, request: WSGIRequest, **kwargs: typing.Any) -> typing.Self:
        """Create an Event given a Django request object."""

        return cls.objects.create(
            remote_ip=request.META.get("REMOTE_ADDR", "0.0.0.0"),  # noqa: S104
            headers=dict(request.headers),
            **kwargs,
        )

    def get_admin_url(self) -> str:
        return reverse(
            f"admin:{self._meta.app_label}_{self._meta.model_name}_change", args=[self.pk]
        )

    @classmethod
    @abstractmethod
    def get_signing_secrets(cls, request: WSGIRequest) -> list[str]:
        """Return signing secrets for this receiver."""
        raise NotImplementedError

    @abstractmethod
    def process_payload(self) -> None:
        raise NotImplementedError(
            f"{self._meta.app_label}.{self._meta.model_name} must implement the method 'process'"
        )

    def process(self) -> None:
        """Create an Event given a Django request object."""

        if isinstance(self.payload, (str, bytes, bytearray)):
            try:
                self.payload = json.loads(self.payload)
            except ValueError:
                self.status = WebhookEventStatus.INVALID
                self.save()
                return

        try:
            self.process_payload()
        except Exception:  # noqa: BLE001
            self.status = WebhookEventStatus.FAILED
            self.traceback = format_exc()
        else:
            self.status = WebhookEventStatus.DONE
        self.save()
