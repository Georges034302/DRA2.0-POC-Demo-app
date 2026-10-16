# Usage

- Execution, testing, and deployment require prior written permission under the [license](../LICENSE).
- Run commands from the repository root.

## Run Locally

**Requirements:** Docker Engine and Docker Compose.

```sh
cp .env.example .env
```

- In `.env`, set strong, unique values for `INTERNAL_API_TOKEN`, `DEMO_USERNAME`, and `DEMO_PASSWORD`.
- Never commit `.env`.

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

## Azure Scripts

- Use the repository scripts for Azure provisioning, publishing, and deployment.
- This section references scripts; it is not an Azure setup walkthrough.
- **Tools:** Git, Docker, Python 3.12, Azure CLI, and GitHub CLI.
- **Access:** An authorized Azure session and access to the private broker image.
- Required environment variables are declared in each script.
- Variable and secret mappings are in the [release workflow](../.github/workflows/ci-cd.yml) and [post-deployment workflow](../.github/workflows/post-deployment.yml).

| Step | Script | Responsibility |
| --- | --- | --- |
| Provision | [setup.sh](../scripts/setup.sh) | Validate prerequisites and call [env-setup.sh](../scripts/env-setup.sh) to create the resource group, ACR, and Container Apps environment. |
| Build | [build.sh](../scripts/build.sh) | Build the three application images locally. With `--publish`, build and push to ACR, then save immutable digests in `BUILD_MANIFEST`. |
| Review | [review.sh](../scripts/review.sh) | Prepare pre-deployment evidence and invoke the pinned AI-Broker image. |
| Deploy | [deploy.sh](../scripts/deploy.sh) | Deploy the manifest's image digests for `GITHUB_SHA` to Container Apps without rebuilding. |
| Verify | [post-deploy.sh](../scripts/post-deploy.sh) | Collect revision, log, and health evidence, then run a separate post-deployment broker scan. |

- Configure Azure OIDC federation and workflow permissions separately.
- Deployment may need permission to assign `AcrPull` roles.
- Pin `BROKER_IMAGE_DIGEST` to an approved GHCR digest.
- Provide a GHCR token with `read:packages` access.
- Store provider keys and application credentials in protected secrets.
- Use the release workflow for gated deployment; the deployment script alone does not enforce broker review or human approval.

## Release Review

- Manually dispatch the [release workflow](../.github/workflows/ci-cd.yml) to test, publish, review, and deploy.
- Automatic runs on pushes to `main` are currently disabled.
- `FAIL` and `ERROR` block release.
- `APPROVAL_REQUIRED` needs human approval through the protected `dra-approval` environment and `APPROVAL_GATE_ENABLED=true`.
- Configure required reviewers before enabling approval-based releases.
- All other required checks must also pass.
- The separate [post-deployment workflow](../.github/workflows/post-deployment.yml) verifies deployment and retains evidence for 30 days.
- AI-Broker scans evidence and reports policy outcomes only.
- It does not build, deploy, roll back, or provide continuous monitoring.

## Limitations

- Azure deployment does not configure persistent SQLite storage. Database container restarts or replacement may lose data.
- Review evidence is sent to an external model provider. Never include secrets in code changes or evidence.
- The private AI-Broker is maintained separately and is not included in this repository.

[Documentation index](index.MD)