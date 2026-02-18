# Deployment Guide

Deployment guide for the Identity Service Banking eKYC API to Google Cloud Run.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`) installed
- [uv](https://docs.astral.sh/uv/) package manager

---

## 1. Running Locally

```bash
docker-compose up --build
```

- App: [http://localhost:8080](http://localhost:8080)
- Swagger: [http://localhost:8080/docs](http://localhost:8080/docs)

```bash
docker-compose down
```

---

## 2. GCP Setup

```bash
gcloud auth login
export PROJECT_ID="your-project-id"
export REGION="us-central1"
gcloud config set project $PROJECT_ID
```

---

## 3. Artifact Registry

```bash
# Create repository (run once)
gcloud artifacts repositories create identity-service \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker images for identity service"

# Grant permission to Cloud Build
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

> **Note:** GCR (`gcr.io`) is deprecated. Always use Artifact Registry (`REGION-docker.pkg.dev/...`).

---

## 4. Build & Push Image

```bash
gcloud builds submit \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/identity-service/identity-service-banking-ekyc .
```

> You need to create a `.gcloudignore` file to ensure `uv.lock` and `config.yaml` are uploaded to Cloud Build (as they are in `.gitignore`).

---

## 5. Google Secret Manager

```bash
# Enable API
gcloud services enable secretmanager.googleapis.com

# Create secret from config.yaml
gcloud secrets create application-config --data-file=config.yaml

# Update secret (when config changes)
gcloud secrets versions add application-config --data-file=config.yaml

# Grant read permission to Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 6. Deploy to Cloud Run

```bash
gcloud run deploy identity-service-banking-ekyc \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/identity-service/identity-service-banking-ekyc:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --set-secrets="/app/secrets/config.yaml=application-config:latest" \
  --max-instances 1 \
  --min-instances 0
```

---

## 7. CI/CD with GitHub Actions

### Workflows

| Workflow | Trigger | Function |
| :--- | :--- | :--- |
| `ci.yml` | Push/PR to `main` | Lint (`ruff`) + Test (`pytest`) |
| `deploy.yml` | Push to `main` | CI → Update Secret → Build → Push → Deploy |

### 7a. Create Service Account

```bash
# Create SA
gcloud iam service-accounts create github-deployer \
  --display-name="GitHub Actions Deployer"

SA_EMAIL="github-deployer@$PROJECT_ID.iam.gserviceaccount.com"

# Grant permissions
for ROLE in roles/artifactregistry.writer roles/run.admin roles/iam.serviceAccountUser roles/secretmanager.secretVersionAdder; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$ROLE"
done
```

### 7b. Workload Identity Federation (instead of SA Key)

> **Required if organization policy disables SA Key creation** (`iam.disableServiceAccountKeyCreation`).

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
GITHUB_REPO="your-github-user/your-repo-name"

# 1. Create pool
gcloud iam workload-identity-pools create "github-pool" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# 2. Create provider (REQUIRED --attribute-condition)
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Actions Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository == '$GITHUB_REPO'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 3. Allow GitHub to impersonate SA
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/$GITHUB_REPO"
```

### 7c. GitHub Secrets

Go to repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret Name | Content |
| :--- | :--- |
| `APPLICATION_CONFIG` | Entire content of production `config.yaml` |

---

## 8. Required Code Changes for Cloud Run

```python
# config.py — Add sslmode=require (Required for Neon DB)
@property
def DATABASE_URL(self) -> str:
    return f"postgresql://...?sslmode=require"

# database.py — Add connect timeout (avoid hanging at startup)
create_engine(db_url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)

# main.py — Use /tmp for log (Cloud Run filesystem is read-only)
logging.FileHandler("/tmp/app.log")
```

---

## 9. Troubleshooting

| Error | Cause | Fix |
| :--- | :--- | :--- |
| `gcr.io repo does not exist` | GCR deprecated | Use Artifact Registry |
| `uploadArtifacts denied` | SA missing permission | Grant `roles/artifactregistry.writer` |
| `stat uv.lock: not exist` | `.gcloudignore` missing | Create `.gcloudignore` |
| `fastapi: not found` | WORKDIR builder ≠ runtime | Set WORKDIR to `/app` in builder stage |
| `secret access denied` | SA missing permission | Grant `roles/secretmanager.secretAccessor` |
| `invalid_target` WIF | Provider not created | Create provider with `--attribute-condition` |
| `versions.add denied` | SA missing permission | Grant `roles/secretmanager.secretVersionAdder` |
| `workflow not reusable` | Missing `workflow_call` | Add `workflow_call:` to `on:` in `ci.yml` |
| `uv.lock not found --frozen` | `uv.lock` is gitignored | Remove `uv.lock` from `.gitignore` |
| `Container failed to start` | Log file on read-only FS | Change to `/tmp/app.log` |
| `Container failed to start` | DB hanging (missing SSL/timeout) | Add `sslmode=require` + `connect_timeout` |
