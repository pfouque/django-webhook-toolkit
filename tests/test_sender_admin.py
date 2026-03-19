from __future__ import annotations

import datetime as dt
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.test import TestCase
from django.utils import timezone

from webhook_toolkit.choices import WebhookEventStatus
from webhook_toolkit.choices import WebhookSubscriptionStatus
from webhook_toolkit.sender.admin import WebhookEventAdmin
from webhook_toolkit.sender.admin import WebhookSubscriptionAdmin
from webhook_toolkit.sender.models import WebhookEvent
from webhook_toolkit.sender.models import WebhookSubscription


class SenderAdminTestCase(TestCase):
    def test_admin_replay_selected_events_resets_and_executes(self) -> None:
        subscription = WebhookSubscription.objects.create(
            description="Acme",
            endpoint_url="https://example.com/webhook",
            status=WebhookSubscriptionStatus.ACTIVE,
        )
        event = WebhookEvent.objects.create(
            subscription=subscription,
            status=WebhookEventStatus.ABORTED,
            retry_count=3,
            retry_after=timezone.now() + dt.timedelta(days=30),
            payload={"hello": "world"},
        )

        assert event.retry_after > timezone.now()

        with patch.object(WebhookEvent, "execute") as execute_mock:
            WebhookEventAdmin(WebhookEvent, admin_site=AdminSite()).replay_selected_events(
                request=RequestFactory().get("/"),
                queryset=WebhookEvent.objects.filter(pk=event.pk),
            )

        event.refresh_from_db()
        assert event.status == WebhookEventStatus.PENDING
        assert event.retry_count == 0
        assert event.retry_after < timezone.now()
        execute_mock.assert_called_once()

    def test_admin_mark_selected_events_for_retry_sets_pending(self) -> None:
        subscription = WebhookSubscription.objects.create(
            description="Acme",
            endpoint_url="https://example.com/webhook",
            status=WebhookSubscriptionStatus.ACTIVE,
        )
        event = WebhookEvent.objects.create(
            subscription=subscription,
            status=WebhookEventStatus.ABORTED,
            retry_count=2,
            retry_after=timezone.now(),
            payload={"ok": True},
        )

        site = AdminSite()
        request = RequestFactory().get("/")
        WebhookEventAdmin(WebhookEvent, site).mark_selected_events_for_retry(
            request,
            WebhookEvent.objects.filter(pk=event.pk),
        )

        event.refresh_from_db()
        assert event.status == WebhookEventStatus.PENDING
        assert event.retry_count == 0

    def test_admin_filters_configured(self) -> None:
        site = AdminSite()
        event_admin = WebhookEventAdmin(WebhookEvent, site)
        subscription_admin = WebhookSubscriptionAdmin(WebhookSubscription, site)

        assert "status" in event_admin.list_filter
        assert "created_at" in event_admin.list_filter
        assert "status" in subscription_admin.list_filter
