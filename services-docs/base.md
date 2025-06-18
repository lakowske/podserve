# Base Service Configuration

## Key Components

**Base Image**: debian:12-slim  
**Purpose**: Common base image for all PodServe services

## Pre-installed Packages

- **Basic utilities**: curl, wget, ca-certificates
- **Network tools**: net-tools, iproute2, ping, dig
- **Python**: python3, pip, venv, common libraries (yaml, jinja2, requests, cryptography)
- **SSL/Security**: openssl, ssl-cert
- **Text processing**: gettext-base, sed, gawk
- **Process management**: procps, psmisc
- **Development tools**: Claude Code CLI for debugging and editing code within containers

## Default Configuration

- **User**: Creates podserve user (UID/GID 1000)
- **Timezone**: UTC (configurable via TZ environment variable)
- **Directories**: Creates /data/config, /data/logs, /data/state
- **Python**: PEP 668 compliant package installation via apt

## Volume Mounts

- `/data/config`: Configuration files
- `/data/logs`: Application logs
- `/data/state`: Persistent state data

## Usage

This is a base image that other services extend. It provides common dependencies and directory structure to reduce duplication across service containers.

### Debugging with Claude Code

The base image includes Claude Code CLI to help debug and edit configurations within running containers:

```bash
# Access container with Claude Code
podman exec -it <container-name> /bin/bash
claude-code

# Or directly run Claude Code commands
podman exec -it <container-name> claude-code --help
```

This enables real-time debugging, configuration editing, and code analysis without rebuilding containers.