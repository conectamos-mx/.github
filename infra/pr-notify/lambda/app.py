"""Webhook de la org conectamos-mx -> Slack, sin GitHub Actions (PLA-1771).

GitHub (webhook de org) -> Function URL -> esta Lambda -> Slack.
  pull_request -> pr_notify     ([ PR LOG ])
  workflow_run -> deploy_notify ([ DEPLOYMENT LOG ])
"""

import base64
import hashlib
import hmac
import json

import deploy_notify
import pr_notify
from common import response, secret

HANDLERS = {"pull_request": pr_notify.handle, "workflow_run": deploy_notify.handle}


def _signature_ok(body, signature):
    expected = "sha256=" + hmac.new(
        secret("GITHUB_WEBHOOK_SECRET_ID").encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    body = event.get("body") or ""
    body = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode()

    if not _signature_ok(body, headers.get("x-hub-signature-256")):
        return response(401, "firma inválida")

    gh_event = headers.get("x-github-event")
    if gh_event == "ping":
        return response(200, "pong")
    handle = HANDLERS.get(gh_event)
    if handle is None:
        return response(204, "")
    return handle(json.loads(body))
