# Shell-Based Implementation

This is the original implementation using shell scripts and traditional service configuration files.

## Structure

```
shell-based/
├── docker/
│   ├── base/           # Base Debian image
│   ├── mail/           # Postfix/Dovecot configuration
│   ├── apache/         # Apache with WebDAV/GitWeb
│   ├── dns/            # BIND 9 configuration
│   ├── certbot/        # Certificate management
│   └── build.sh        # Build script
├── scripts/
│   ├── benchmark.sh    # Performance testing
│   └── test.sh         # Integration testing
├── src/
│   └── podserve/       # Minimal Python CLI
└── deploy/
    ├── simple.yaml     # Basic pod deployment
    ├── nginx.yaml      # Nginx variant
    └── certificates.yaml # Cert management
```

## Key Features

- Direct service configuration files
- Shell scripts for service management
- Proven and tested in production
- Minimal abstraction layer
- Fast startup times

## Usage

```bash
# Build all images
cd docker && ./build.sh

# Deploy pod
podman play kube deploy/simple.yaml

# Run tests
./scripts/test.sh
```

This implementation is stable and production-ready.