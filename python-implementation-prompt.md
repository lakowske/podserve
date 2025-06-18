# Python Implementation Prompt for Claude

You are tasked with implementing the Python unified framework for PodServe based on the service documentation in `/services-docs/`. This implementation should create a consistent, maintainable framework for all services.

## Context
- Review `/services-docs/*-implementation.md` files for detailed specifications
- Reference `/implementations/shell-based/` for working configurations
- Follow patterns established in `/services-docs/base-implementation.md`
- Ensure compatibility with existing tests in `/shared/tests/`

## Implementation Requirements

### 1. Base Framework (`/opt/podserve/core/`)
Create these core modules:
- `config.py` - Environment variable management with defaults
- `service.py` - BaseService abstract class with lifecycle methods
- `health.py` - Health check framework
- `logging.py` - Dual logging (stdout + files)
- `utils.py` - Common utilities

### 2. Service Implementations (`/opt/podserve/services/`)
Implement each service extending BaseService:
- `mail.py` - Postfix/Dovecot management
- `apache.py` - Apache with SSL/WebDAV/GitWeb
- `dns.py` - BIND9 configuration
- `certbot.py` - Certificate management

### 3. Key Design Principles
- **Configuration**: Use Jinja2 templates for service configs
- **Logging**: Implement dual logging (console + file)
- **Process Management**: Proper signal handling
- **Health Checks**: HTTP endpoints for each service
- **Development Mode**: Support host-mounted code

### 4. Critical Implementation Details

#### Logging Setup
```python
# Every service must log to both stdout and /data/logs/
# Use RotatingFileHandler for file logs
# Ensure all subprocess output is captured
```

#### Service Lifecycle
```python
# Handle SIGTERM gracefully
# Implement proper startup/shutdown sequences
# Validate configurations before starting services
```

#### Configuration Management
```python
# Load from environment variables
# Support defaults in code
# Render templates with proper escaping
```

### 5. Testing Compatibility
Ensure implementation passes existing tests:
- Container startup times < 10 seconds
- Graceful shutdown < 5 seconds
- All health checks respond correctly
- Log output visible via `podman logs`

### 6. File Structure
Create in `/implementations/python-unified/`:
```
src/podserve/
├── __init__.py
├── __main__.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── service.py
│   ├── health.py
│   ├── logging.py
│   └── utils.py
├── services/
│   ├── __init__.py
│   ├── mail.py
│   ├── apache.py
│   ├── dns.py
│   └── certbot.py
└── templates/
    ├── mail/
    ├── apache/
    └── dns/
```

### 7. Docker Integration
- Base image installs framework at `/opt/podserve/`
- Service images extend base with specific packages
- Support both production (COPY) and development (mount) modes

## Success Criteria
1. All services start successfully
2. Logs appear in both `podman logs` and `/data/logs/`
3. Configuration templates render correctly
4. Health checks pass
5. Graceful shutdown works
6. Development mode allows live code updates

## References
- Check `/CLAUDE.md` for lessons learned
- Use `/implementations/shell-based/docker/*/config/` for working configurations
- Follow `/services-docs/development-workflow.md` for dev setup

Remember: Focus on clarity, maintainability, and consistency across all services.