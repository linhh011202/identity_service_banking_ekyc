# Deployment Guide

This guide explains how to deploy the Identity Service Banking eKYC API.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed.
- [Docker Compose](https://docs.docker.com/compose/install/) installed (usually included with Docker Desktop/Engine).

## Running Locally

To run the application using the configuration in `config.yaml`:

1.  **Start the service**:
    ```bash
    docker-compose up --build
    ```
    This command will:
    - Build the `app` image from the current directory.
    - Start the service.
    - Validates connection to the database defined in `config.yaml`.
    - The application will be available at [http://localhost:8080](http://localhost:8080).
    - The API documentation (Swagger UI) will be at [http://localhost:8080/docs](http://localhost:8080/docs).

2.  **Stop the service**:
    ```bash
    docker-compose down
    ```

## Google Cloud Run Deployment

This guide assumes you have the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`) installed and initialized.

### 1. Setup and Authentication

Login to Google Cloud and configure Docker authentication:

```bash
gcloud auth login
gcloud auth configure-docker
```

Set your project ID and preferred region:

```bash
export PROJECT_ID="your-project-id"
export REGION="asia-southeast1" # Example region
gcloud config set project $PROJECT_ID
```

### 2. Build and Push Container

We use **Artifact Registry** to store Docker images.

**A. Create Repository (One time setup)**
```bash
gcloud artifacts repositories create identity-service \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker images for identity service"
```

**B. Build and Push**
Use Cloud Build to build and push the image to Artifact Registry keys.

```bash
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/$PROJECT_ID/identity-service/identity-service-banking-ekyc .
```

### 3. Deploy to Cloud Run

Deploy the service using the `gcloud run deploy` command.

> **Note**: For production, it is highly recommended to use [Secret Manager](https://cloud.google.com/run/docs/configuring/secrets) (see section 4).

If you are **NOT** using Secret Manager (testing only):

```bash
gcloud run deploy identity-service-banking-ekyc \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/identity-service/identity-service-banking-ekyc:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars POSTGRES_USER="your-db-user" \
  --set-env-vars POSTGRES_PASSWORD="your-db-password" \
  --set-env-vars POSTGRES_DB="your-db-name" \
  --set-env-vars POSTGRES_HOST="your-db-host" \
  --set-env-vars POSTGRES_PORT="5432"
```

*Note: The environment variables above are examples based on your `config.yaml`. Replace them with your actual production secrets.*
### 4. Using Google Secret Manager (Advanced & Secure)

Instead of passing sensitive environment variables, you can upload your `config.yaml` to Secret Manager and mount it into the container.

1.  **Enable the API**:
    ```bash
    gcloud services enable secretmanager.googleapis.com
    ```

2.  **Create the Secret**:
    Upload your production `config.yaml`:
    ```bash
    gcloud secrets create application-config --data-file=config.yaml
    ```

3.  **Grant Access**:
    Allow the Cloud Run service account to access the secret.
    
    *Find your service account*:
    By default, Cloud Run uses the **Compute Engine default service account**. You can find it by running:
    
    ```bash
    gcloud projects describe $PROJECT_ID --format="value(projectNumber)"
    ```
    
    The email will be: `[PROJECT_NUMBER]-compute@developer.gserviceaccount.com`
    
    Replace `YOUR_SERVICE_ACCOUNT_EMAIL` below with that email.

    ```bash
    # Example: 123456789-compute@developer.gserviceaccount.com
    gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL" \
      --role="roles/secretmanager.secretAccessor"
    ```

4.  **Deploy with Secret Mount**:
    Mount the secret as a file at `/app/secrets/config.yaml`. The application is already configured to read from this path via `CONFIG_PATH` env var (default in Dockerfile).
    
    ```bash
    gcloud run deploy identity-service-banking-ekyc \
      --image us-central1-docker.pkg.dev/$PROJECT_ID/identity-service/identity-service-banking-ekyc:latest \
      --platform managed \
      --region us-central1 \
      --allow-unauthenticated \
      --port 8080 \
      --set-secrets="/app/secrets/config.yaml=application-config:latest" \
      --max-instances 1 \
      --min-instances 0
    ```

---

## CI/CD with GitHub Actions

The project includes two GitHub Actions workflows in `.github/workflows/`.

### CI (`ci.yml`)

Runs on every **push** and **pull request** to `main`.

| Job | What it does |
| :--- | :--- |
| **Lint** | `ruff check .` and `ruff format --check .` |
| **Test** | `pytest tests/ -v` (runs after lint passes) |

### Deploy (`deploy.yml`)

Runs on **push to `main`** only, after CI passes.

| Step | What it does |
| :--- | :--- |
| CI | Runs the full CI workflow first |
| Auth | Authenticates to GCP using `GCP_SA_KEY` secret |
| Build | Builds Docker image, tags with commit SHA |
| Push | Pushes to Artifact Registry |
| Deploy | Deploys to Cloud Run with Secret Manager mount |

### Setup: Create GCP Service Account Key

To enable GitHub Actions to deploy, you need to create a service account key and store it as a GitHub secret.

1.  **Create the key**:
    ```bash
    gcloud iam service-accounts keys create key.json \
      --iam-account=YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com
    ```

2.  **Add to GitHub**:
    - Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
    - Click **New repository secret**
    - Name: `GCP_SA_KEY`
    - Value: paste the entire contents of `key.json`

3.  **Delete the local key** (for security):
    ```bash
    rm key.json
    ```

> [!CAUTION]
> Never commit `key.json` to your repository. It is already excluded by `.gitignore`.
