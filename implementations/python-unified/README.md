# Python Unified Implementation

This implementation uses a unified Python framework for all services, as described in the service documentation at `/services-docs/`.

## Structure

```
python-unified/
├── docker/
│   ├── base/           # Base image with Python framework
│   ├── mail/           # Mail service container
│   ├── web/            # Web service container
│   ├── dns/            # DNS service container
│   └── build.sh        # Build script
├── src/
│   └── podserve/       # Python package
│       ├── core/       # Framework (config, service base, health)
│       └── services/   # Service implementations
└── deploy/
    ├── simple.yaml     # Production deployment
    └── dev.yaml        # Development with host mounts
```

## Key Features

- Unified Python framework at `/opt/podserve/`
- Template-based configuration using Jinja2
- Consistent service management across all containers
- Development mode with host-mounted code
- Claude Code CLI for in-container debugging

## Development Workflow

1. Build base image with framework
2. Build service images
3. Deploy with `dev.yaml` for host-mounted code
4. Edit code on host - changes reflect immediately
5. Use Claude Code for in-container debugging

See `/services-docs/` for detailed implementation guides.