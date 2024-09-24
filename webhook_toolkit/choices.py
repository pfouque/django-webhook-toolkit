from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class WebhookSubscriptionStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    PAUSED = "PAUSED", _("Paused")
    DELETED = "DELETED", _("Deleted")


class WebhookEventStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    DONE = "DONE", _("Done")
    INVALID = "INVALID", _("Invalid")  # Unprocessable
    IGNORED = "IGNORED", _("Ignored")  # processable (unmanaged event_type)
    FAILED = "FAILED", _("Failed")  # processable but failed
    ABORTED = "ABORTED", _("Aborted")  # processable but failed
