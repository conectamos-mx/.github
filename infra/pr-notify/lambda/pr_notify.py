"""Avisos de PR a Slack desde el webhook de la org (PLA-1771).

Reemplaza a pr-notify.yml + pr-notification.yml: mismo mensaje, mismo canal,
sin un job de Actions por evento (cada uno se cobraba como 1 minuto).
"""

import os
from datetime import datetime, timezone

from common import notify, response, secret

ACTIONS = {"opened", "ready_for_review", "reopened", "closed", "review_requested"}
REPOS = {r.strip() for r in os.environ.get("REPOS", "").split(",") if r.strip()}


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


def handle(payload):
    if payload.get("action") not in ACTIONS:
        return response(204, "")
    if REPOS and payload["repository"]["name"] not in REPOS:
        return response(204, "")
    return notify(secret("SLACK_WEBHOOK_URL_ID"), build_text(payload))
