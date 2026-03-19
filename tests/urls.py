from __future__ import annotations

from django.contrib import admin
from django.urls import path

from tests.testapp.views import AcmeWebhookReceiverView

urlpatterns = [
    path("admin/", admin.site.urls, name="admin"),
    path("webhooks/acme/", AcmeWebhookReceiverView.as_view(), name="acme-webhook"),
]
