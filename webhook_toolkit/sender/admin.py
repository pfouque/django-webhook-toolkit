from __future__ import annotations

import typing

from django.contrib import admin
from django.utils import timezone

from webhook_toolkit.choices import WebhookEventStatus

from .models import WebhookEvent
from .models import WebhookEventLog
from .models import WebhookSubscription

if typing.TYPE_CHECKING:
    from django.db import models
    from django.http import HttpRequest


@admin.register(WebhookSubscription)
class WebhookSubscriptionAdmin(admin.ModelAdmin[WebhookSubscription]):
    list_display = ("uuid", "description", "endpoint_url", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("uuid", "description", "endpoint_url")
    date_hierarchy = "created_at"


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin[WebhookEvent]):
    list_display = ("uuid", "subscription", "status", "retry_count", "retry_after", "created_at")
    list_filter = ("status", "created_at", "subscription__status")
    search_fields = ("uuid", "subscription__uuid", "subscription__endpoint_url")
    date_hierarchy = "created_at"
    actions = ["replay_selected_events", "mark_selected_events_for_retry"]

    @admin.action(description="Replay selected events now")
    def replay_selected_events(
        self, request: HttpRequest, queryset: models.QuerySet[WebhookEvent]
    ) -> None:
        for webhook_event in queryset.select_related("subscription"):
            webhook_event.reset_for_retry()
            webhook_event.execute()

    @admin.action(description="Mark selected events for retry (pending)")
    def mark_selected_events_for_retry(
        self, request: HttpRequest, queryset: models.QuerySet[WebhookEvent]
    ) -> None:
        now = timezone.now()
        for webhook_event in queryset:
            webhook_event.status = WebhookEventStatus.PENDING
            webhook_event.retry_count = 0
            webhook_event.retry_after = now
            webhook_event.save(update_fields=["status", "retry_count", "retry_after"])


@admin.register(WebhookEventLog)
class WebhookEventLogAdmin(admin.ModelAdmin[WebhookEventLog]):
    list_display = ("uuid", "webhook_event", "response_status_code", "retry_number", "created_at")
    list_filter = ("response_status_code", "created_at")
    search_fields = ("uuid", "webhook_event__uuid")
    date_hierarchy = "created_at"
