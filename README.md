# Aegis Deploy

**Production deployment harness for the [Aegis](https://github.com/lakshmi-mahabaleshwara/aegis) medical image de-identification pipeline.**

Aegis Deploy wraps the Aegis core library inside a **MONAI Deploy Application Package (MAP)**, orchestrated by **Argo Workflows** on **Amazon EKS**, with config-driven QA/Prod environments and AWS-native infrastructure.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Ingestion & Raw Storage                                            │
│  ┌──────────────────┐  ┌──────────────────────┐                     │
│  │ Amazon S3         │  │ AWS HealthImaging     │                    │
│  │ (PNG/JPEG Input)  │  │ (Raw DICOM Studies)   │                    │
│  └────────┬─────────┘  └──────────┬───────────┘                     │
│           └───────────┬───────────┘                                  │
│                       ▼                                              │
│  ┌─────────────────────────────────────────┐                         │
│  │ Argo Workflows (Scheduler & DAG)        │                         │
│  │ ┌─────────┐  ┌──────────┐  ┌─────────┐ │                         │
│  │ │Discovery│→ │DeID      │→ │Finalize │ │                         │
│  │ │Operator │  │Workers   │  │         │ │                         │
│  │ └─────────┘  └──────────┘  └─────────┘ │                         │
│  └─────────────────────────────────────────┘                         │
│                       ▼                                              │
│  ┌──────────────────────────────────────────┐                        │
│  │ EKS GPU Cluster — MAP/Worker Pods        │                        │
│  │ • DICOM Tag Scrubbing                    │                        │
│  │ • UID Remapping (Deterministic Hash)     │                        │
│  │ • OCR / PHI Masking (EasyOCR + NER)      │                        │
│  └──────────────────────────────────────────┘                        │
│                       ▼                                              │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐                  │
│  │Clean S3  │  │Identity Vault│  │Analytics      │                   │
│  │+ Health  │  │(RDS Private) │  │Lakehouse      │                   │
│  │Imaging   │  │              │  │(Iceberg on S3)│                   │
│  └──────────┘  └──────────────┘  └───────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
aegis-deploy/
├── aegis_deploy/                  # Python package
│   ├── cli.py                     # CLI entry point (discover / run)
│   ├── config/                    # Config module
│   │   ├── config_loader.py       # YAML loader with env var interpolation
│   │   ├── base.yaml              # Shared defaults
│   │   ├── qa.yaml                # QA overlay
│   │   └── prod.yaml              # Production overlay
│   ├── map/                       # MONAI Application Package wrapper
│   │   ├── app.py                 # MAP Application (operator DAG)
│   │   ├── deid_operator.py       # De-identification operator (wraps aegis)
│   │   └── storage_operator.py    # Clean storage + vault writer
│   ├── operators/                 # Pipeline operators
│   │   ├── discovery.py           # Discovery operator (S3/HealthImaging scanner)
│   │   └── manifest.py            # Manifest dataclass + fan-out logic
│   └── vault/                     # Identity Vault
│       ├── models.py              # SQLAlchemy models
│       ├── repository.py          # CRUD repository
│       └── migrations/            # SQL migrations
├── argo/                          # Argo Workflow templates
│   ├── cron-workflow.yaml         # Scheduled trigger
│   └── deid-dag.yaml              # DAG: discover → workers → finalize
├── infrastructure/                # Terraform IaC
│   ├── main.tf                    # Provider & backend
│   ├── variables.tf               # All variables
│   ├── eks.tf                     # EKS cluster + GPU nodes
│   ├── s3.tf                      # S3 buckets
│   ├── rds.tf                     # Identity Vault RDS
│   └── secrets.tf                 # Secrets Manager
├── tests/                         # Unit tests
├── Dockerfile                     # Multi-stage MAP container
├── pyproject.toml                 # PEP 621 package config
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (for container builds)
- AWS CLI configured (for S3/RDS access)

### Install

```bash
# Clone and install
git clone <repo-url>
cd aegis-deploy
pip install -e ".[dev]"
```

### Configuration

Config is environment-aware. Set `AEGIS_DEPLOY_ENV` to switch between environments:

```bash
# QA (default) — CPU-only, debug logging, dev buckets
export AEGIS_DEPLOY_ENV=qa

# Production — GPU NER, CloudWatch, production buckets
export AEGIS_DEPLOY_ENV=prod
```

All settings support `${VAR_NAME:default}` interpolation from environment variables.

### Run Locally

```bash
# Discover new images and generate a manifest
aegis-deploy discover --output manifest.json

# Run the de-identification pipeline
aegis-deploy run --manifest manifest.json

# Run a single chunk (for testing fan-out)
aegis-deploy run --manifest manifest.json --chunk-index 0
```

### Docker

```bash
# Build
docker build -t aegis-deploy:latest .

# Run discovery
docker run --rm \
  -e AEGIS_DEPLOY_ENV=qa \
  aegis-deploy:latest discover --output /tmp/manifest.json

# Run pipeline
docker run --rm \
  -e AEGIS_DEPLOY_ENV=qa \
  -v ./manifest.json:/tmp/manifest.json:ro \
  aegis-deploy:latest run --manifest /tmp/manifest.json
```

### Tests

```bash
# Run all unit tests
python -m pytest tests/unit/ -v

# With coverage
python -m pytest tests/unit/ -v --cov=aegis_deploy --cov-report=term-missing
```

---

## Infrastructure

Terraform scaffolding is in `infrastructure/`. To deploy:

```bash
cd infrastructure
terraform init
terraform plan -var="environment=qa" -var="vpc_id=vpc-xxx" -var='private_subnet_ids=["subnet-xxx"]'
terraform apply
```

> **Note:** Provide your AWS account VPC/subnet IDs and review the plan before applying.

---

## Argo Workflows

Deploy the workflow templates to your EKS cluster:

```bash
kubectl apply -f argo/deid-dag.yaml
kubectl apply -f argo/cron-workflow.yaml
```

The CronWorkflow runs nightly at 2:00 AM UTC. Adjust the schedule in `argo/cron-workflow.yaml`.

---

## License

Apache 2.0

## Acknowledgments

- [Aegis](https://github.com/lakshmi-mahabaleshwara/aegis) — Core de-identification engine
- [MONAI Deploy](https://docs.monai.io/) — Medical AI application packaging
- [Argo Workflows](https://argoproj.github.io/argo-workflows/) — Kubernetes-native orchestration
