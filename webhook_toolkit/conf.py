from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings as django_settings

# All attributes accessed with this prefix are possible to overwrite
# through django.conf.settings.
settings_prefix = "WEBHOOKS_"


@dataclass(frozen=True)
class AppSettings:
    """Access this instance as ``my_app.conf.app_settings``."""

    WEBHOOKS_SENDER_MAX_RETRY: int = 10
    """The number of retry."""

    WEBHOOKS_RECEIVER_DEFAULT_RETENTION_DAYS: int | None = 10
    """The number of days retention logs will be stored."""

    WEBHOOKS_RECEIVER_TIMESTAMP_TOLERANCE: int = 300
    """Maximum allowed timestamp skew in seconds."""

    def __getattribute__(self, __name: str) -> Any:  # noqa: PYI063
        """
        Check if a Django project settings should override the app default.

        To avoid returning random properties of the django settings, we inspect the prefix first.
        """

        if __name.startswith(settings_prefix) and hasattr(django_settings, __name):
            return getattr(django_settings, __name)

        return super().__getattribute__(__name)


app_settings = AppSettings()
