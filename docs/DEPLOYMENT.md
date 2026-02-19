# Deployment Guide

Deployment guide for the Identity Service Banking eKYC API to Google Kubernetes Engine (GKE).

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`) installed
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed
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
export PROJECT_ID="banking-ekyc-487718"
export REGION="us-central1"
export CLUSTER_NAME="banking-ekyc-cluster"
gcloud config set project $PROJECT_ID
```

### Configure kubectl

```bash
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION
```

---

## 3. Artifact Registry

```bash
# Create repository (run once)
gcloud artifacts repositories create identity-service \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker images for identity service"

# Grant permission to Cloud Build (if using Cloud Build triggers)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

> **Note:** GCR (`gcr.io`) is deprecated. Always use Artifact Registry (`REGION-docker.pkg.dev/...`).

---

## 4. Build & Push Image

```bash
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/identity-service/identity-service-banking-ekyc:latest .

# Push
docker push $REGION-docker.pkg.dev/$PROJECT_ID/identity-service/identity-service-banking-ekyc:latest
```

---

## 5. Kubernetes Configuration (GitOps)

The Kubernetes manifests are stored in a separate repository (e.g., `gke_banking_ekyc`) or a `k8s-config` directory.

### Cloning Configuration (if separate repo)

```bash
git clone https://github.com/linhh011202/gke_banking_ekyc.git k8s-config
cd k8s-config
```

### Secrets Management

Secrets (like database credentials) are managed via Google Secret Manager and synced or injected into the cluster.
In our `deploy.yml`, we fetch the config from Secret Manager and create a Kubernetes Secret.

```bash
# Create manual secret (for testing)
kubectl create secret generic identity-service-secrets \
  --from-file=config.yaml=./config.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 6. Deploy to GKE

```bash
# Update image tag in deployment.yaml
sed -i "s|image: .*|image: $REGION-docker.pkg.dev/$PROJECT_ID/identity-service/identity-service-banking-ekyc:latest|g" k8s-config/deployment.yaml

# Apply manifests
kubectl apply -f k8s-config/deployment.yaml
kubectl apply -f k8s-config/service.yaml
```

To check status:

```bash
kubectl get pods
kubectl get services
```

---

## 7. CI/CD with GitHub Actions

### Workflows

| Workflow | Trigger | Function |
| :--- | :--- | :--- |
| `ci.yml` | Push/PR to `main` | Lint (`ruff`) + Test (`pytest`) |
| `deploy.yml` | Push to `main` | CI → Configure GKE creds → Create Secret → Deploy manifests |

### 7a. Service Account Permissions

The service account used by GitHub Actions (`github-deployer`) requires the following roles:

*   `roles/artifactregistry.writer` (Push images)
*   `roles/container.developer` (Deploy to GKE)
*   `roles/secretmanager.secretAccessor` (Read secrets)
*   `roles/secretmanager.secretVersionAdder` (Add secret versions)
*   `roles/iam.serviceAccountUser` (Act as service account)

```bash
SA_EMAIL="github-deployer@$PROJECT_ID.iam.gserviceaccount.com"

# Grant permissions
for ROLE in roles/artifactregistry.writer roles/container.developer roles/secretmanager.secretAccessor roles/secretmanager.secretVersionAdder roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$ROLE"
done
```

### 7b. GitHub Secrets

| Secret Name | Content |
| :--- | :--- |
| `APPLICATION_CONFIG` | Entire content of production `config.yaml` |

---

## 8. Required Code Changes

Ensure your application is container-ready:

*   **Database**: Use `sslmode=require` for Neon DB.
*   **Logging**: Log to stdout/stderr (e.g., using `uvicorn` default logging) or a writable path like `/tmp` if file logging is needed.
*   **Health Checks**: Ensure `/health` or `/` endpoint is available for Kubernetes liveness/readiness probes.

---

## 9. Troubleshooting

| Error | Cause | Fix |
| :--- | :--- | :--- |
| `files list file for package '...' is missing final newline` | Apt/dpkg corruption in image | Rebuild base image or clear apt cache in Dockerfile |
| `ImagePullBackOff` | Docker image not found or private | Check image URL and ImagePullSecrets (or Workload Identity on node) |
| `CrashLoopBackOff` | App crashing on start | Check logs: `kubectl logs <pod-name>` |
| `ResponseError: code=403 ... container.clusters.get` | SA missing GKE permission | Grant `roles/container.developer` |
| `CreateContainerConfigError` | Missing Secret/ConfigMap | Ensure `kubectl create secret` step ran successfully |
