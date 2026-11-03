"""Lo compartido por los avisos de PR y de deploy: secretos, respuestas y Slack."""

import json
import os
import urllib.request

import boto3

_secrets = {}


def secret(env_name):
    # Se leen una vez por contenedor: el valor vive en Secrets Manager, no en Terraform.
    if env_name not in _secrets:
        sm = boto3.client("secretsmanager")
        _secrets[env_name] = sm.get_secret_value(SecretId=os.environ[env_name])["SecretString"].strip()
    return _secrets[env_name]


def response(status, text):
    return {"statusCode": status, "headers": {"Content-Type": "text/plain"}, "body": text}


def post_to_slack(url, text):
    data = json.dumps({"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]})
    req = urllib.request.Request(
        url,
        data=data.encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        resp.read()


def notify(url, text):
    try:
        post_to_slack(url, text)
    except Exception as exc:  # noqa: BLE001 — GitHub muestra la entrega fallida y se puede reenviar
        print(f"Slack rechazó el aviso: {exc}")
        return response(502, "slack falló")
    return response(200, "ok")
