from __future__ import annotations

import abc
import hashlib
import hmac
from typing import Mapping

from standardwebhooks.webhooks import Webhook

from webhook_toolkit.signing import build_signature_header


class SignatureVerificationError(ValueError):
    pass


class SignatureMechanism(abc.ABC):
    name: str

    @abc.abstractmethod
    def sign_headers(
        self,
        *,
        payload: bytes,
        webhook_id: str | None,
        timestamp: int | None,
        secrets: list[str],
    ) -> dict[str, str]:
        raise NotImplementedError

    @abc.abstractmethod
    def verify(
        self,
        *,
        payload: bytes,
        headers: Mapping[str, str],
        secrets: list[str],
        tolerance: int | None,
    ) -> tuple[str | None, int | None]:
        raise NotImplementedError


class StandardWebhooksMechanism(SignatureMechanism):
    name = "standardwebhooks"

    def sign_headers(
        self,
        *,
        payload: bytes,
        webhook_id: str | None,
        timestamp: int | None,
        secrets: list[str],
    ) -> dict[str, str]:
        if not secrets:
            return {}
        if not webhook_id or timestamp is None:
            raise SignatureVerificationError("Standard Webhooks requires webhook_id and timestamp.")
        signature = build_signature_header(
            webhook_id=webhook_id,
            timestamp=timestamp,
            payload=payload,
            secrets=secrets,
        )
        return {
            "webhook-id": webhook_id,
            "webhook-timestamp": str(timestamp),
            "webhook-signature": signature,
        }

    def verify(
        self,
        *,
        payload: bytes,
        headers: Mapping[str, str],
        secrets: list[str],
        tolerance: int | None,
    ) -> tuple[str | None, int | None]:
        webhook_id = headers.get("webhook-id")
        webhook_timestamp = headers.get("webhook-timestamp")
        webhook_signature = headers.get("webhook-signature")

        if not webhook_id or not webhook_timestamp or not webhook_signature:
            raise SignatureVerificationError("Missing webhook signature headers.")

        try:
            timestamp_int = int(webhook_timestamp)
        except (TypeError, ValueError) as exc:
            raise SignatureVerificationError("Invalid webhook-timestamp.") from exc

        if tolerance:
            import time

            now = int(time.time())
            if abs(now - timestamp_int) > tolerance:
                raise SignatureVerificationError("Timestamp outside tolerance.")

        normalized_headers = {key.lower(): value for key, value in headers.items()}
        for secret in secrets:
            try:
                Webhook(secret).verify(payload, normalized_headers)
            except Exception:  # noqa: BLE001, PERF203, S112
                continue
            else:
                return webhook_id, timestamp_int

        raise SignatureVerificationError("Invalid signature.")


class Sha256Mechanism(SignatureMechanism):
    name = "sha256"
    signature_header: str
    signature_prefix: str
    timestamp_header: str | None = None
    requires_timestamp: bool = False

    def build_message(self, payload: bytes, timestamp: int | None) -> bytes:
        return payload

    def _compute_digest(self, secret: str, message: bytes) -> str:
        return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    def sign_headers(
        self,
        *,
        payload: bytes,
        webhook_id: str | None,
        timestamp: int | None,
        secrets: list[str],
    ) -> dict[str, str]:
        if not secrets:
            return {}
        if self.requires_timestamp and timestamp is None:
            raise SignatureVerificationError("Timestamp required for signing.")

        message = self.build_message(payload, timestamp)
        secret = secrets[0]
        digest = self._compute_digest(secret, message)
        headers = {self.signature_header: f"{self.signature_prefix}{digest}"}
        if self.timestamp_header and timestamp is not None:
            headers[self.timestamp_header] = str(timestamp)
        return headers

    def verify(
        self,
        *,
        payload: bytes,
        headers: Mapping[str, str],
        secrets: list[str],
        tolerance: int | None,
    ) -> tuple[str | None, int | None]:
        normalized_headers = {key.lower(): value for key, value in headers.items()}
        signature = normalized_headers.get(self.signature_header)
        if not signature or not signature.startswith(self.signature_prefix):
            raise SignatureVerificationError("Missing or invalid signature header.")

        timestamp_int: int | None = None
        if self.timestamp_header:
            timestamp_value = normalized_headers.get(self.timestamp_header)
            if timestamp_value is None:
                if self.requires_timestamp:
                    raise SignatureVerificationError("Missing timestamp header.")
            else:
                try:
                    timestamp_int = int(timestamp_value)
                except (TypeError, ValueError) as exc:
                    raise SignatureVerificationError("Invalid timestamp.") from exc

        if self.requires_timestamp and tolerance and timestamp_int is not None:
            import time

            now = int(time.time())
            if abs(now - timestamp_int) > tolerance:
                raise SignatureVerificationError("Timestamp outside tolerance.")

        provided = signature.split(self.signature_prefix, 1)[1]
        message = self.build_message(payload, timestamp_int)
        for secret in secrets:
            digest = self._compute_digest(secret, message)
            if hmac.compare_digest(provided, digest):
                return None, timestamp_int

        raise SignatureVerificationError("Invalid signature.")


class GitHubHmacSha256Mechanism(Sha256Mechanism):
    name = "github-hmac-sha256"
    signature_header = "x-hub-signature-256"
    signature_prefix = "sha256="


class SlackV0Mechanism(Sha256Mechanism):
    name = "slack-v0"
    signature_header = "x-slack-signature"
    signature_prefix = "v0="
    timestamp_header = "x-slack-request-timestamp"
    requires_timestamp = True
    version = "v0"

    def build_message(self, payload: bytes, timestamp: int | None) -> bytes:
        if timestamp is None:
            raise SignatureVerificationError("Slack signing requires a timestamp.")
        return f"{self.version}:{timestamp}:".encode() + payload


MECHANISMS: dict[str, type[SignatureMechanism]] = {
    StandardWebhooksMechanism.name: StandardWebhooksMechanism,
    Sha256Mechanism.name: Sha256Mechanism,
    GitHubHmacSha256Mechanism.name: GitHubHmacSha256Mechanism,
    SlackV0Mechanism.name: SlackV0Mechanism,
}


def get_signature_mechanism(name: str | None) -> SignatureMechanism:
    mechanism_name = name or StandardWebhooksMechanism.name
    try:
        mechanism_cls = MECHANISMS[mechanism_name]
    except KeyError as exc:
        raise SignatureVerificationError(
            f"Unknown signature mechanism '{mechanism_name}'."
        ) from exc
    return mechanism_cls()
