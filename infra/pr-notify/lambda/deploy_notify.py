"""Avisos de deploy a Slack desde el webhook de la org (evento workflow_run).

Reemplaza al paso actions/deploy-notify (y al job de notification.yml): el aviso
sale cuando termina el workflow de deploy, sin que el workflow haga nada.
Mismo [ DEPLOYMENT LOG ]; cada repo va a su canal (default: devops-alerts).
"""

import json
import os
from datetime import datetime, timezone

from common import notify, response, secret

# {repo: {service, workflow, prod_url, dev_url}} — var.deploy_services de Terraform.
SERVICES = json.loads(os.environ.get("DEPLOY_SERVICES") or "{}")

OK = {"success"}
FAILED = {"failure", "cancelled", "timed_out", "startup_failure"}


def _members_map():
    # Opcional: sin el secreto (o vacío) el aviso sale igual, sin mención.
    if not os.environ.get("SLACK_MEMBERS_MAP_ID"):
        return {}
    try:
        return json.loads(secret("SLACK_MEMBERS_MAP_ID") or "{}")
    except Exception as exc:  # noqa: BLE001
        print(f"SLACK_MEMBERS_MAP ilegible: {exc}")
        return {}


def environment(run):
    # El evento no trae los inputs de workflow_dispatch: se deduce de la rama,
    # igual que el default de los deploy.yml.
    return "Production" if run["head_branch"] == "main" else "Development"


def build_text(payload, cfg, members=None):
    """Mismo formato que actions/deploy-notify."""
    run = payload["workflow_run"]
    service = cfg.get("service") or payload["repository"]["name"]
    env = environment(run)
    actor = (run.get("triggering_actor") or run.get("actor") or {}).get("login", "")
    commit_msg = ((run.get("head_commit") or {}).get("message") or "").split("\n")[0]
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if run["conclusion"] in OK:
        status_line = f"✅ *Deployment exitoso - {service}*"
        url = cfg.get("prod_url" if env == "Production" else "dev_url") or "N/A"
        tail = ""
    else:
        status_line = f"❌ *Deployment falló - {service}*"
        url = "N/A"
        tail = f"\n🔗 *Run:* <{run['html_url']}|ver logs>"
        slack_id = (members or {}).get(actor)
        if slack_id:
            tail += f"\n<@{slack_id}> "

    return (
        f"*[ DEPLOYMENT LOG ]*\n{status_line}\n\n"
        f"🌐 *URL:* {url}\n"
        f"📦 *Servicio:* {service} ({env})\n"
        f"🔨 *Commit:* {commit_msg or 'Manual deployment'} (`{run['head_sha'][:7]}`)\n"
        f"👤 *Por:* {actor}\n"
        f"⏰ *Hora:* {now_utc}{tail}"
    )


def handle(payload):
    if payload.get("action") != "completed":
        return response(204, "")
    run = payload["workflow_run"]
    repo = payload["repository"]["name"]
    cfg = SERVICES.get(repo)
    if cfg is None:
        return response(204, "")
    if run.get("path", "").split("@")[0] != cfg.get("workflow", ".github/workflows/deploy.yml"):
        return response(204, "")
    if run.get("conclusion") not in OK | FAILED:
        return response(204, "")  # skipped, neutral, action_required…

    members = _members_map() if run["conclusion"] in FAILED else {}
    webhooks = json.loads(secret("DEPLOY_SLACK_WEBHOOKS_ID"))
    url = webhooks.get(repo) or webhooks["default"]
    return notify(url, build_text(payload, cfg, members))
