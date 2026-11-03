# pr-notify

Avisos de PR y de deploy a Slack sin GitHub Actions (PLA-1771). Reemplaza a
`pr-notify.yml` + `pr-notification.yml` y al aviso de cada `deploy.yml`: cada
aviso era un job de ~10 s que GitHub cobraba como 1 minuto.

```
GitHub (webhook de la org) → Function URL → Lambda (app.py) → Slack
  pull_request → pr_notify.py     [ PR LOG ]
  workflow_run → deploy_notify.py [ DEPLOYMENT LOG ]
```

### PRs (`pr_notify.py`)

- **Eventos:** `opened`, `ready_for_review`, `reopened`, `review_requested`, `closed` (mergeada o no).
- **Repos:** `var.repos` (los que tenían `pr-notify.yml`: `platform-api`, `conectamos-platform`, `brain`, `brightcell-api`, `zoe-integration`, `os`). Vacío = todos.
- **Mensaje:** el mismo `[ PR LOG ]` de `pr-notification.yml`, al mismo canal.

### Deploys (`deploy_notify.py`)

- **Evento:** `workflow_run` `completed` del workflow de deploy (`.github/workflows/deploy.yml`
  por default) de un repo de `var.deploy_services`. Otro repo u otro workflow: 204.
- **Estado:** `success` → ✅; `failure`, `cancelled`, `timed_out` → ❌ con link al run y
  mención al actor (`deploy-notify/SLACK_MEMBERS_MAP`). `skipped` no avisa.
- **Entorno:** por la rama — `main` → Production, otra → Development (el evento no trae
  los inputs de `workflow_dispatch`).
- **Canal:** `deploy-notify/SLACK_WEBHOOKS`, JSON `{repo: url}`; la clave `default`
  (devops-alerts) cubre a los que no están.
- **Repo nuevo:** sumarlo a `var.deploy_services` (servicio + URLs), `apply`, y borrar
  el aviso de su `deploy.yml`. Canal propio: agregar su clave al JSON del secreto.

### Común
- **Seguridad:** la Function URL es pública; todo lo que no traiga la firma
  `X-Hub-Signature-256` del secret del webhook responde 401.
- **Fallos:** si Slack no responde, la Lambda devuelve 502 y GitHub marca la entrega
  como fallida (Settings → Webhooks → Recent Deliveries → *Redeliver*).

Cuenta AWS: prod (`114743615563`, perfil `conectamos-prod`). State en
`s3://conectamos-tfstate-prod/pr-notify/terraform.tfstate`. Una sola Lambda para
todos los repos de la org.

## Aplicar

Se aplica a mano: el stack cambia casi nunca y así no hay workflow ni rol OIDC que mantener.

```bash
aws login --profile conectamos-prod
# Terraform no entiende las credenciales de `aws login`: se le pasan exportadas.
eval "$(aws configure export-credentials --profile conectamos-prod --format env)"
terraform init
terraform apply
```

## Primera vez

1. `terraform apply` crea los secretos vacíos, la Lambda y la URL (`terraform output webhook_url`).
2. Cargar los valores (nunca pasan por Terraform):

   ```bash
   aws secretsmanager put-secret-value --secret-id pr-notify/SLACK_WEBHOOK_URL \
     --secret-string 'https://hooks.slack.com/services/…'   # el mismo valor que el secret PR_ALERTS_URL
   aws secretsmanager put-secret-value --secret-id pr-notify/GITHUB_WEBHOOK_SECRET \
     --secret-string "$(openssl rand -hex 32)"               # guardarlo: va en el paso 3
   ```

3. Webhook de la org (requiere owner de `conectamos-mx`): *Settings → Webhooks → Add webhook*
   - Payload URL: `terraform output -raw webhook_url`
   - Content type: `application/json`
   - Secret: el mismo de `pr-notify/GITHUB_WEBHOOK_SECRET`
   - Events: *Let me select individual events* → **Pull requests**

   - Events: además, **Workflow runs** (avisos de deploy).

   GitHub manda un `ping` al crearlo; debe responder 200.
4. Abrir un PR de prueba en uno de los repos y ver el aviso en el canal (llegará dos veces
   mientras siga `pr-notify.yml`). Verificado, se borra `pr-notify.yml` de los tres repos.

## Rotar un secreto

`put-secret-value` con el valor nuevo y, para que la Lambda lo lea ya (lo cachea por
contenedor), `aws lambda update-function-configuration --function-name pr-notify --description "rotado $(date +%F)"`.
Si es el del webhook, actualizarlo también en GitHub.

## Logs

```bash
aws logs tail /aws/lambda/pr-notify --since 1h --profile conectamos-prod
```
