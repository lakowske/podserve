# Development Workflow

## Overview

Enable rapid development by mounting host code into containers while maintaining production-ready builds.

## Code Organization

```
podserve/
├── pyproject.toml          # Project dependencies
├── src/podserve/          # Python package (mounted in dev)
│   ├── core/              # Framework code
│   └── services/          # Service implementations
└── docker/                # Dockerfiles
```

## Container Strategy

### Base Image Build
- Install Python venv with all dependencies from `pyproject.toml`
- Copy framework to `/opt/podserve/` for production
- Include Claude Code CLI for debugging

### Development Workflow
1. **Volume Mount**: Mount `./src/podserve` to `/opt/podserve` in containers
2. **Same Paths**: Code runs identically whether copied or mounted
3. **No Switches**: Services always use `/opt/podserve/` path

### Pod Configuration

Production (`simple.yaml`):
```yaml
# No volume mounts - uses copied code
```

Development (`dev.yaml`):
```yaml
volumes:
  - name: podserve-src
    hostPath:
      path: ./src/podserve
containers:
  - volumeMounts:
    - name: podserve-src
      mountPath: /opt/podserve
```

## Benefits

- **Single codebase**: Same code structure for dev and production
- **Fast iteration**: Edit on host, changes immediate in container
- **Claude Code**: Debug/edit directly in containers
- **No rebuild**: Only rebuild when dependencies change

## Implementation Notes

- Virtual environment pre-built in base image
- Services always run from `/opt/podserve/`
- Mount overwrites copied code in development
- Production images are self-contained