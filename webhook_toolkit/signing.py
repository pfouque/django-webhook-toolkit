from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Iterable


class WebhookSignatureError(ValueError):
    pass


def _normalize_secret(secret: str | bytes) -> bytes:
    if isinstance(secret, bytes):
        return secret
    if secret.startswith("whsec_"):
        return base64.b64decode(secret[len("whsec_") :])
    return secret.encode("utf-8")


def _to_bytes(value: str | bytes) -> bytes:
    return value if isinstance(value, bytes) else value.encode("utf-8")


def build_signed_message(webhook_id: str, timestamp: int, payload: bytes) -> bytes:
    if "." in webhook_id:
        raise WebhookSignatureError("webhook_id must not contain '.'")
    return f"{webhook_id}.{timestamp}.".encode() + payload


def compute_signature(secret: str | bytes, message: bytes) -> str:
    secret_bytes = _normalize_secret(secret)
    digest = hmac.new(secret_bytes, message, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def build_signature_header(
    webhook_id: str, timestamp: int, payload: bytes, secrets: Iterable[str | bytes]
) -> str:
    message = build_signed_message(webhook_id, timestamp, payload)
    signatures = [f"v1,{compute_signature(secret, message)}" for secret in secrets]
    return " ".join(signatures)


def verify_signature_header(
    signature_header: str,
    webhook_id: str,
    timestamp: int,
    payload: bytes,
    secrets: Iterable[str | bytes],
) -> None:
    provided = [part.strip() for part in signature_header.split() if part.strip()]
    if not provided:
        raise WebhookSignatureError("Missing webhook-signature header")

    message = build_signed_message(webhook_id, timestamp, payload)
    expected = [compute_signature(secret, message) for secret in secrets]

    for candidate in provided:
        if not candidate.startswith("v1,"):
            continue
        provided_sig = _to_bytes(candidate.split(",", 1)[1])
        for exp in expected:
            if hmac.compare_digest(provided_sig, _to_bytes(exp)):
                return

    raise WebhookSignatureError("Invalid webhook signature")
