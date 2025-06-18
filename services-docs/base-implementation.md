# Base Service Implementation Plan

## Overview

The base service provides the foundation Python framework that all other services will use. This includes common utilities, configuration management, and service lifecycle management.

## Python Package Structure

```
/opt/podserve/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── service.py         # Base service class
│   ├── health.py          # Health check framework
│   └── utils.py           # Common utilities
├── services/
│   ├── __init__.py
│   ├── apache.py
│   ├── certbot.py
│   ├── dns.py
│   └── mail.py
└── templates/             # Jinja2 templates for config files
```

## Core Components

### 1. Configuration Management (core/config.py)

```python
class ConfigManager:
    - Load environment variables with defaults
    - Support for YAML/JSON config files
    - Template rendering with Jinja2
    - Config validation
```

### 2. Base Service Class (core/service.py)

```python
class BaseService:
    - Service lifecycle management (start, stop, reload)
    - Signal handling (SIGTERM, SIGINT)
    - Logging configuration
    - Health check integration
    - Directory creation and permissions
```

### 3. Health Check Framework (core/health.py)

```python
class HealthCheck:
    - HTTP health endpoint
    - Custom health check methods
    - Readiness vs liveness probes
```

### 4. Common Utilities (core/utils.py)

```python
- File operations with proper permissions
- Process management helpers
- SSL certificate validation
- Network utilities
```

## Dockerfile Changes

```dockerfile
FROM debian:12-slim

# Install system packages (as before)
...

# Install Python framework
COPY podserve/ /opt/podserve/
RUN cd /opt/podserve && \
    python3 -m pip install --break-system-packages -e .

# Set PYTHONPATH
ENV PYTHONPATH=/opt/podserve

# Default entrypoint
ENTRYPOINT ["python3", "-m", "podserve"]
```

## Implementation Steps

1. Create the Python package structure
2. Implement ConfigManager with environment variable loading
3. Create BaseService abstract class with lifecycle methods
4. Implement health check framework
5. Add common utilities for file/process management
6. Create setup.py for package installation
7. Update Dockerfile to include Python code