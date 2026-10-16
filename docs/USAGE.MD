# Usage

Execution, testing, and deployment require prior written permission under the [license](../LICENSE). Run the commands below from the repository root.

## Run Locally

**Requirements:** Docker Engine and Docker Compose.

```sh
cp .env.example .env
```

Edit `.env`: replace `INTERNAL_API_TOKEN`, `DEMO_USERNAME`, and `DEMO_PASSWORD` with strong, unique values. Never commit `.env`.

```sh
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080) and sign in with your configured credentials.

```sh
curl http://localhost:8080/health
```

- SQLite data persists in a named volume. `docker compose down` stops the app; adding `-v` deletes its data.
- Dynamic task actions require browser internet access: HTMX 2.0.4 loads from jsDelivr.

## Test and Build

**Requirements:** Python 3.12 and Docker.

```sh
python -m pip install \
  -r frontend/requirements.txt \
  -r backend/requirements.txt \
  -r database/requirements.txt
python -m pytest frontend/tests backend/tests database/tests -q
bash -n scripts/*.sh
bash scripts/build.sh
```

## Azure Setup

**Requirements:** Git, Docker, Python 3.12, Azure CLI, GitHub CLI, and access to the private broker image.

1. Configure GitHub Actions OIDC federation and Azure permissions for ACR push and Container Apps deployment. Initial deployment may also need permission to assign `AcrPull` roles.
2. Authenticate to Azure and provision the shared resources:

```sh
az login
az account set --subscription YOUR_SUBSCRIPTION_ID
export AZURE_RESOURCE_GROUP=your-resource-group
export AZURE_LOCATION=your-azure-region
export AZURE_ACR_NAME=youruniqueregistryname
export AZURE_CONTAINERAPPS_ENV=your-container-apps-environment
bash scripts/setup.sh
```

The setup script creates the resource group, registry, and Container Apps environment; it does not configure OIDC.

3. Publish the private broker image and configure the repository settings below.
4. Configure required reviewers on the `dra-approval` environment before setting `APPROVAL_GATE_ENABLED=true`.

### Repository Variables

| Variables | Purpose |
| --- | --- |
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | Azure OIDC identity and subscription. |
| `AZURE_RESOURCE_GROUP`, `AZURE_LOCATION` | Target resource group and region. |
| `AZURE_ACR_NAME`, `AZURE_CONTAINERAPPS_ENV` | Registry and Container Apps environment. |
| `AZURE_FRONTEND_APP`, `AZURE_BACKEND_APP`, `AZURE_DATABASE_APP` | Container App names. |
| `GHCR_USER` | Account with access to the private broker package. |
| `BROKER_IMAGE_DIGEST` | Pinned reference: `ghcr.io/OWNER/IMAGE@sha256:...`. |
| `AI_PROVIDER` | `gemini` or `groq`. |
| `GEMINI_MODEL`, `GROQ_MODEL` | Model setting for the selected provider. |
| `APPROVAL_GATE_ENABLED` | Enable only after required reviewers are configured. |

### Repository Secrets

| Secrets | Purpose |
| --- | --- |
| `GHCR_READ_TOKEN` | Private broker package access with `read:packages`. |
| `GEMINI_API_KEY`, `GROQ_API_KEY` | Set the key for the selected provider. |
| `INTERNAL_API_TOKEN` | Authentication between application services. |
| `DEMO_USERNAME`, `DEMO_PASSWORD` | Demo sign-in credentials. |

## Release Review

The release workflow tests the app, publishes immutable image digests to ACR, and invokes the pinned broker. Deployment uses the reviewed digests without rebuilding.

`FAIL` and `ERROR` block release. `APPROVAL_REQUIRED` requires the protected approval environment and `APPROVAL_GATE_ENABLED=true`.

The separate post-deployment workflow checks Azure revisions and health, then invokes the broker. Its evidence is retained for 30 days; verification provides neither rollback nor ongoing monitoring.

## Limitations

- Azure deployment does not configure persistent SQLite storage. Database container restarts or replacement may lose data.
- Review evidence is sent to an external model provider. Never include secrets in code changes or evidence.
- The private AI-Broker is maintained separately and is not included in this repository.

[Documentation index](index.MD)