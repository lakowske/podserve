# PodServe

An integrated server pod providing web, mail, and DNS services in a single Podman pod.

## Project Structure

This project supports multiple implementation approaches:

```
├── services-docs/          # Service implementation guides
├── implementations/        # Different implementation attempts
│   ├── shell-based/       # Current shell script implementation
│   └── python-unified/    # Python framework implementation (in progress)
├── shared/                # Resources shared across implementations
│   ├── docs/             # General documentation
│   ├── tests/            # Test suite
│   └── tools/            # Development and performance tools
├── pyproject.toml         # Python project configuration
├── Makefile               # Build commands with implementation selection
└── CLAUDE.md              # Development notes and lessons learned
```

## Quick Start

```bash
# Select implementation (default: shell-based)
export IMPL=shell-based

# Deploy the complete pod
podman play kube implementations/$IMPL/deploy/simple.yaml

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

## Implementation Approaches

### shell-based
The original implementation using shell scripts and traditional service configuration files.
- Proven and tested
- Direct service configuration
- Minimal abstraction

### python-unified
A new implementation using a unified Python framework (in development).
- Consistent service management
- Template-based configuration
- Enhanced debugging capabilities

## Documentation

- **[Usage Guide](shared/docs/USAGE.md)** - Complete deployment and management guide
- **[Architecture](shared/docs/ARCHITECTURE.md)** - System design and components
- **[Container Comparison](shared/docs/CONTAINER-COMPARISON.md)** - Technology analysis
- **[Service Docs](services-docs/)** - Implementation guides for each service

## Development

```bash
# Set up development environment
make dev-setup

# Build container images for specific implementation
make build IMPL=shell-based

# Run tests
make test

# Performance benchmarks
make benchmark

# Deploy for testing
make deploy IMPL=shell-based
```

## Requirements

- Podman 4.0 or higher
- At least 15GB storage for persistent volumes
- Network ports: 53, 80, 443, 25, 587, 143, 993, 995

## License

See project license file for details.