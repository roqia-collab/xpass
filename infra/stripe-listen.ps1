# Relais local des webhooks Stripe. Lit PSP_SECRET_KEY dans .env, sans l'afficher.
$root = Split-Path $PSScriptRoot -Parent
Get-Content (Join-Path $root ".env") | ForEach-Object {
  if ($_ -match '^\s*PSP_SECRET_KEY=(.*)$') { $env:STRIPE_API_KEY = $Matches[1].Trim() }
}
if (-not $env:STRIPE_API_KEY) { throw "PSP_SECRET_KEY manquante dans .env" }
Set-Location $root
npx --yes @stripe/cli listen --forward-to http://localhost:8000/api/v1/payments/webhooks/stripe --events checkout.session.completed,checkout.session.async_payment_succeeded,invoice.paid,invoice.payment_succeeded,invoice.payment_failed,customer.subscription.updated,customer.subscription.deleted,transfer.created,transfer.reversed,account.updated
