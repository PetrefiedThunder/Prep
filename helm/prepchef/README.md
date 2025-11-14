# PrepChef Helm Chart

This Helm chart deploys the PrepChef platform to Kubernetes.

## Prerequisites

- Kubernetes 1.23+
- Helm 3.8+
- kubectl configured to communicate with your cluster

## Installation

```bash
# Install the chart
helm install prepchef ./helm/prepchef -n prepchef --create-namespace

# Install with custom values
helm install prepchef ./helm/prepchef -n prepchef -f custom-values.yaml
```

## Validation

Validate manifests before installation:

```bash
# Using kubeval (install from https://kubeval.instrumenta.dev/)
helm template prepchef ./helm/prepchef | kubeval --strict

# Using kubectl
helm template prepchef ./helm/prepchef | kubectl apply --dry-run=client -f -
```

## Configuration

See `values.yaml` for all configuration options.

Key configuration areas:
- Image tags and repositories
- Resource limits and requests
- Autoscaling parameters
- Ingress hostnames
- Secret management

## Secrets

The chart includes placeholder secrets. For production:

1. Create secrets externally:
```bash
kubectl create secret generic prepchef-secrets \
  --from-literal=DATABASE_URL='postgresql://...' \
  --from-literal=REDIS_URL='redis://...' \
  --from-literal=JWT_SECRET='...' \
  --from-literal=STRIPE_SECRET_KEY='sk_live_...' \
  --from-literal=STRIPE_WEBHOOK_SECRET='whsec_...' \
  --from-literal=MINIO_SECRET_KEY='...' \
  -n prepchef
```

2. Or use external secrets manager (recommended):
   - HashiCorp Vault
   - AWS Secrets Manager
   - Azure Key Vault
   - Google Secret Manager

## Upgrading

```bash
helm upgrade prepchef ./helm/prepchef -n prepchef
```

## Uninstallation

```bash
helm uninstall prepchef -n prepchef
```
