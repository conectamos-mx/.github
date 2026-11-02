# =============================================================================
# pr-notify — avisos de PR a Slack sin GitHub Actions (PLA-1771)
# Webhook de la org (evento pull_request) -> Function URL -> Lambda -> Slack.
# =============================================================================

locals {
  name = "pr-notify"
}

# -----------------------------------------------------------------------------
# Secretos: Terraform crea SOLO el contenedor (mismo criterio que PLA-1765 en
# platform-api). El valor se carga con `put-secret-value` y no pasa por el state.
# -----------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "slack_webhook_url" {
  name        = "${local.name}/SLACK_WEBHOOK_URL"
  description = "Incoming webhook del canal de avisos de PR (el valor de PR_ALERTS_URL)"
}

resource "aws_secretsmanager_secret" "github_webhook_secret" {
  name        = "${local.name}/GITHUB_WEBHOOK_SECRET"
  description = "Secret del webhook de la org conectamos-mx (firma X-Hub-Signature-256)"
}

# -----------------------------------------------------------------------------
# Lambda
# -----------------------------------------------------------------------------

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/lambda/pr_notify.py"
  output_path = "${path.module}/lambda/pr_notify.zip"
}

resource "aws_iam_role" "lambda" {
  name = local.name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "secrets" {
  name = "${local.name}-secrets"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "secretsmanager:GetSecretValue"
      Resource = [
        aws_secretsmanager_secret.slack_webhook_url.arn,
        aws_secretsmanager_secret.github_webhook_secret.arn,
      ]
    }]
  })
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = 14
}

resource "aws_lambda_function" "pr_notify" {
  function_name    = local.name
  role             = aws_iam_role.lambda.arn
  handler          = "pr_notify.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 15

  environment {
    variables = {
      REPOS                    = join(",", var.repos)
      SLACK_WEBHOOK_URL_ID     = aws_secretsmanager_secret.slack_webhook_url.arn
      GITHUB_WEBHOOK_SECRET_ID = aws_secretsmanager_secret.github_webhook_secret.arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
}

# Pública a propósito: GitHub no firma con IAM. La Lambda rechaza (401) todo lo
# que no traiga la firma HMAC del secret del webhook.
resource "aws_lambda_function_url" "pr_notify" {
  function_name      = aws_lambda_function.pr_notify.function_name
  authorization_type = "NONE"
}

# lambda:InvokeFunctionUrl (FunctionURLAllowPublicAccess) lo agrega AWS solo al
# crear la URL con auth NONE; declararlo acá choca (409). Falta InvokeFunction:
# sin él la URL responde 403. Queda acotado a la URL, así nadie invoca la Lambda
# directo por su API.
resource "aws_lambda_permission" "invoke_via_url" {
  statement_id             = "FunctionURLAllowInvokeAction"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.pr_notify.function_name
  principal                = "*"
  invoked_via_function_url = true
}
