#!/usr/bin/env bash
# One-time Google setup for the monthly SEO loop (.github/workflows/seo-loop.yml) - keyless.
#
# Run it in Google Cloud Shell (console.cloud.google.com -> the >_ button, top right) with the
# project you want picked at the top of the console. Paste the whole thing; it's safe to run twice.
#
# What it does:
#   - turns on the Search Console API (and the APIs keyless sign-in needs)
#   - makes a "seo-loop" service account - no roles, no key
#   - lets GitHub sign in as it, but only for workflows in jackwilkins738-oss/dash, an hour at a time
#     (Workload Identity Federation - no key is ever created, so your organisation's
#     "no service account keys" policy stays on)
# It prints the three things to copy: the email for Search Console and the two GitHub variables.
set -euo pipefail

REPO="jackwilkins738-oss/dash"
PROJECT="$(gcloud config get-value project 2>/dev/null)"
if [ -z "$PROJECT" ]; then
  echo "Pick a project at the top of the Cloud console first (or: gcloud config set project YOUR_PROJECT)." >&2
  exit 1
fi
NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
SA="seo-loop@${PROJECT}.iam.gserviceaccount.com"

gcloud services enable searchconsole.googleapis.com iamcredentials.googleapis.com sts.googleapis.com iam.googleapis.com

gcloud iam service-accounts describe "$SA" >/dev/null 2>&1 ||
  gcloud iam service-accounts create seo-loop --display-name="SEO loop (GitHub, keyless)"

gcloud iam workload-identity-pools describe github --location=global >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools create github --location=global --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers describe dash --location=global --workload-identity-pool=github >/dev/null 2>&1 ||
  gcloud iam workload-identity-pools providers create-oidc dash --location=global --workload-identity-pool=github \
    --display-name="jackwilkins738-oss/dash" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository == '${REPO}'"

gcloud iam service-accounts add-iam-policy-binding "$SA" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${REPO}" \
  >/dev/null

cat <<EOF

Done. Now:

1. Search Console -> scalardigital.co.uk -> Settings -> Users and permissions -> Add user
   Email:      ${SA}
   Permission: Restricted

2. GitHub -> ${REPO} -> Settings -> Secrets and variables -> Actions -> Variables tab -> New variable
   GCP_WIF_PROVIDER     projects/${NUMBER}/locations/global/workloadIdentityPools/github/providers/dash
   GCP_SERVICE_ACCOUNT  ${SA}
EOF
