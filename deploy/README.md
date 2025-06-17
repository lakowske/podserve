# Deployment Configurations

This directory contains Kubernetes YAML files for deploying PodServe.

## Files

- **simple.yaml** - Main pod configuration with Apache, Mail, and DNS services
- **certificates.yaml** - Certificate management pod with Let's Encrypt support
- **nginx.yaml** - Alternative nginx-based configuration

## Usage

```bash
# Deploy the main pod
podman play kube deploy/simple.yaml

# Deploy certificate management (optional)
podman play kube deploy/certificates.yaml

# Check deployment status
podman pod ps
podman ps --pod
```

## Configuration

Edit the YAML files to customize:
- Domain names and hostnames
- Environment variables
- Resource limits
- Volume sizes
- Port mappings