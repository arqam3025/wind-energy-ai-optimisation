#!/usr/bin/env bash
# One-time Azure setup for WindGrid continuous deployment. Run it in Azure Cloud Shell (Bash):
#   portal.azure.com -> the ">_" icon -> Bash, then paste:
#   curl -fsSL https://raw.githubusercontent.com/arqam3025/wind-energy-ai-optimisation/main/deploy/azure/bootstrap.sh | bash
#
# It creates, in your subscription:
#   1. a resource group + storage account that hold the Terraform state;
#   2. a user-assigned managed identity that GitHub Actions signs in as, through OpenID Connect
#      (short-lived tokens; no password or secret is stored anywhere);
#   3. a federated credential that trusts only this repository's "main" branch;
#   4. a Contributor role assignment for that identity on the subscription.
# It prints the four values to add in GitHub: Settings -> Secrets and variables -> Actions -> Variables.
# Safe to re-run: existing resources are reused.
set -euo pipefail

REPO="${REPO:-arqam3025/wind-energy-ai-optimisation}"
LOCATION="${LOCATION:-francecentral}"
STATE_RG="rg-windgrid-tfstate"
IDENTITY="id-windgrid-github"

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
echo "Subscription: $(az account show --query name -o tsv) ($SUBSCRIPTION_ID)"

echo "Registering resource providers (first time can take a minute)..."
for provider in Microsoft.App Microsoft.OperationalInsights Microsoft.Storage Microsoft.ManagedIdentity; do
  az provider register --namespace "$provider" --wait >/dev/null
done

echo "Terraform state storage..."
if az group show -n "$STATE_RG" -o none 2>/dev/null; then
  echo "  reusing resource group $STATE_RG ($(az group show -n "$STATE_RG" --query location -o tsv))"
else
  az group create -n "$STATE_RG" -l "$LOCATION" -o none
fi
STORAGE=$(az storage account list -g "$STATE_RG" --query "[0].name" -o tsv)
if [ -z "$STORAGE" ]; then
  STORAGE="stwindgrid$(openssl rand -hex 4)"
  az storage account create -n "$STORAGE" -g "$STATE_RG" -l "$LOCATION" --sku Standard_LRS \
    --min-tls-version TLS1_2 --allow-blob-public-access false -o none
fi
az storage container create -n tfstate --account-name "$STORAGE" --auth-mode login -o none 2>/dev/null || \
  az storage container create -n tfstate --account-name "$STORAGE" -o none

echo "Deployment identity (OIDC)..."
az identity create -n "$IDENTITY" -g "$STATE_RG" -l "$LOCATION" -o none
CLIENT_ID=$(az identity show -n "$IDENTITY" -g "$STATE_RG" --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show -n "$IDENTITY" -g "$STATE_RG" --query principalId -o tsv)
az identity federated-credential create --name github-main --identity-name "$IDENTITY" -g "$STATE_RG" \
  --issuer "https://token.actions.githubusercontent.com" --subject "repo:${REPO}:ref:refs/heads/main" \
  --audiences "api://AzureADTokenExchange" -o none 2>/dev/null || echo "  (federated credential already exists)"

echo "Role assignments (may take a minute to propagate)..."
az role assignment create --assignee-object-id "$PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
  --role Contributor --scope "/subscriptions/$SUBSCRIPTION_ID" -o none 2>/dev/null || true
az role assignment create --assignee-object-id "$PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "$(az storage account show -n "$STORAGE" -g "$STATE_RG" --query id -o tsv)" -o none 2>/dev/null || true

cat <<EOF

Done. In GitHub open: https://github.com/${REPO}/settings/variables/actions
and add these four repository VARIABLES (they are identifiers, not secrets):

  AZURE_CLIENT_ID        ${CLIENT_ID}
  AZURE_TENANT_ID        ${TENANT_ID}
  AZURE_SUBSCRIPTION_ID  ${SUBSCRIPTION_ID}
  TFSTATE_STORAGE        ${STORAGE}

Then make the two container images public (one time), so Azure can pull them:
  https://github.com/arqam3025?tab=packages -> windgrid-api and windgrid-dashboard
  -> Package settings -> Change visibility -> Public

The next push to main deploys automatically (Actions -> Deploy), or run the Deploy workflow manually.
EOF
