"""Avisos de PR a Slack desde el webhook de la org (PLA-1771).

Reemplaza a pr-notify.yml + pr-notification.yml: mismo mensaje, mismo canal,
sin un job de Actions por evento (cada uno se cobraba como 1 minuto).

GitHub (webhook de org, evento pull_request) -> Function URL -> esta Lambda -> Slack.
"""

import base64
import hashlib
import hmac
import json
import os
import urllib.request
from datetime import datetime, timezone

import boto3

ACTIONS = {"opened", "ready_for_review", "reopened", "closed", "review_requested"}
REPOS = {r.strip() for r in os.environ.get("REPOS", "").split(",") if r.strip()}

_secrets = {}


def _secret(name):
    # Se leen una vez por contenedor: el valor vive en Secrets Manager, no en Terraform.
    if name not in _secrets:
        sm = boto3.client("secretsmanager")
        _secrets[name] = sm.get_secret_value(SecretId=os.environ[name])["SecretString"].strip()
    return _secrets[name]


def _response(status, text):
    return {"statusCode": status, "headers": {"Content-Type": "text/plain"}, "body": text}


def _signature_ok(body, signature):
    expected = "sha256=" + hmac.new(
        _secret("GITHUB_WEBHOOK_SECRET_ID").encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def build_text(payload):
    """Mismo formato que pr-notification.yml."""
    action = payload["action"]
    pr = payload["pull_request"]

    if action == "opened":
        header = "🔔 *Nueva PR abierta*"
    elif action == "ready_for_review":
        header = "👀 *PR lista para review*"
    elif action == "review_requested":
        header = "👀 *Review solicitado*"
    elif action == "reopened":
        header = "🔁 *PR reabierta*"
    elif action == "closed":
        header = "✅ *PR mergeada*" if pr.get("merged") else "🚫 *PR cerrada sin merge*"
    else:
        header = "📋 *PR actualizada*"

    reviewer = (payload.get("requested_reviewer") or {}).get("login") or (
        payload.get("requested_team") or {}
    ).get("slug")
    reviewer_line = f"\n👀 *Reviewer:* {reviewer}" if reviewer else ""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return (
        f"*[ PR LOG ]* — {header}\n\n"
        f"🔗 *PR:* <{pr['html_url']}|#{pr['number']} — {pr['title']}>\n"
        f"📦 *Repo:* {payload['repository']['name']}\n"
        f"🌿 *Branches:* `{pr['head']['ref']}` → `{pr['base']['ref']}`\n"
        f"👤 *Autor:* {pr['user']['login']}{reviewer_line}\n"
        f"⏰ *Hora:* {now_utc}"
    )


def _post_to_slack(text):
    data = json.dumps({"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]})
    req = urllib.request.Request(
        _secret("SLACK_WEBHOOK_URL_ID"),
        data=data.encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        resp.read()


def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    body = event.get("body") or ""
    body = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode()

    if not _signature_ok(body, headers.get("x-hub-signature-256")):
        return _response(401, "firma inválida")

    gh_event = headers.get("x-github-event")
    if gh_event == "ping":
        return _response(200, "pong")
    if gh_event != "pull_request":
        return _response(204, "")

    payload = json.loads(body)
    if payload.get("action") not in ACTIONS:
        return _response(204, "")
    if REPOS and payload["repository"]["name"] not in REPOS:
        return _response(204, "")

    try:
        _post_to_slack(build_text(payload))
    except Exception as exc:  # noqa: BLE001 — GitHub muestra la entrega fallida y se puede reenviar
        print(f"Slack rechazó el aviso: {exc}")
        return _response(502, "slack falló")
    return _response(200, "ok")
