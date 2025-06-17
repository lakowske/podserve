# PodServe

An integrated server pod providing web, mail, and DNS services in a single Podman pod.

## Quick Start

```bash
# Deploy the complete pod
podman play kube deploy/simple.yaml

# Check status
podman pod ps
podman ps --pod
```

## Features

- **Web Server**: Apache with SSL, WebDAV, and GitWeb support
- **Mail Server**: Postfix/Dovecot with SMTP, IMAP, and POP3
- **DNS Server**: BIND 9 with recursive resolution
- **Certificate Management**: Let's Encrypt integration
- **Performance Optimized**: Fast startup and shutdown times

## Project Structure

```
├── deploy/           # Kubernetes YAML deployment files
├── docs/             # Documentation
├── docker/           # Container build files and configurations
├── scripts/          # Utility scripts for development and testing
├── src/              # Source code
├── tests/            # Test suite
├── tools/            # Development and performance tools
├── Makefile          # Build and development commands
└── pyproject.toml    # Python project configuration
```

## Documentation

- **[Usage Guide](docs/USAGE.md)** - Complete deployment and management guide
- **[Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[Container Comparison](docs/CONTAINER-COMPARISON.md)** - Technology analysis

## Development

```bash
# Set up development environment
make dev-setup

# Build container images
make build

# Run tests
make test

# Performance benchmarks
make benchmark

# Deploy for testing
make deploy
```

## Requirements

- Podman 4.0 or higher
- At least 15GB storage for persistent volumes
- Network ports: 53, 80, 443, 25, 587, 143, 993, 995

## License

See project license file for details.