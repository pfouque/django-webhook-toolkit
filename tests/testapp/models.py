from __future__ import annotations

try:
    from typing import override
except ImportError:  # pragma: no cover
    # Py<3.12
    from typing_extensions import override


from webhook_toolkit.receiver.models import AbstractWebhookEvent


class AcmeWebhookEvent(AbstractWebhookEvent):
    @override
    @classmethod
    def get_signing_secrets(cls, request):
        return ["whsec_dGVzdHNlY3JldA=="]

    def process_payload(self): ...
