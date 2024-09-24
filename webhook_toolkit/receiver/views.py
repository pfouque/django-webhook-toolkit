from __future__ import annotations

import datetime as dt
import json
import logging
import typing
from http import HTTPStatus
from traceback import format_exc
from typing import Any

from django.http import HttpResponse
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import View

from webhook_toolkit.choices import WebhookEventStatus
from webhook_toolkit.conf import app_settings
from webhook_toolkit.signature_mechanisms import SignatureVerificationError
from webhook_toolkit.signature_mechanisms import get_signature_mechanism

if typing.TYPE_CHECKING:
    from django.core.handlers.wsgi import WSGIRequest
    from django.http.response import HttpResponseBase

    from .models import AbstractWebhookEvent

logger = logging.getLogger(__name__)


class WebhookReceiverView(View):
    # NOTE: https://adamj.eu/tech/2021/05/09/how-to-build-a-webhook-receiver-in-django/

    webhook_event_model: type[AbstractWebhookEvent]
    allowed_methods: list[str] = ["get", "post"]
    retention: int | None = None
    signature_mechanism: str | None = None

    def get(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if "get" not in self.allowed_methods:
            return HttpResponse(status=HTTPStatus.METHOD_NOT_ALLOWED)
        return self.process(request, *args, **kwargs)

    def post(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if "post" not in self.allowed_methods:
            return HttpResponse(status=HTTPStatus.METHOD_NOT_ALLOWED)
        return self.process(request, *args, **kwargs)

    def process(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        webhook_id = request.headers.get("webhook-id")
        webhook_timestamp = request.headers.get("webhook-timestamp")
        secrets = self.webhook_event_model.get_signing_secrets(request)

        if self.signature_mechanism is None:
            return JsonResponse({"error": "Signature mechanism not configured"}, status=500)
        mechanism = get_signature_mechanism(self.signature_mechanism)
        timestamp_int: int | None = None

        if secrets:
            try:
                verified_id, verified_timestamp = mechanism.verify(
                    payload=request.body,
                    headers=request.headers,
                    secrets=secrets,
                    tolerance=app_settings.WEBHOOKS_RECEIVER_TIMESTAMP_TOLERANCE,
                )
            except SignatureVerificationError:
                return JsonResponse({"error": "Invalid signature"}, status=400)
            webhook_id = verified_id or webhook_id
            timestamp_int = verified_timestamp
        elif webhook_timestamp:
            try:
                timestamp_int = int(webhook_timestamp)
            except (TypeError, ValueError):
                timestamp_int = None

        if webhook_id and self.webhook_event_model.objects.filter(webhook_id=webhook_id).exists():
            return HttpResponse(status=HTTPStatus.OK)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Non JSON"}, status=400)

        if ttl := app_settings.WEBHOOKS_RECEIVER_DEFAULT_RETENTION_DAYS:
            self.webhook_event_model.objects.filter(
                created_at__lte=timezone.now() - dt.timedelta(days=ttl)
            ).delete()

        webhook_event = self.webhook_event_model.create_from_request(
            request=request,
            payload=data,
            webhook_id=webhook_id,
            webhook_timestamp=timestamp_int,
        )

        try:
            webhook_event.process()
        except Exception as e:
            logger.exception("Failed to process %s", webhook_event)
            webhook_event.exception = str(e)
            webhook_event.status = WebhookEventStatus.FAILED
            webhook_event.traceback = format_exc()
        finally:
            webhook_event.save(update_fields=["status", "exception", "traceback"])

        return HttpResponse(status=HTTPStatus.OK)
