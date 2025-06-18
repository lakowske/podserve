# PodServe Development Context

This project implements containerized web, mail, and DNS services using Podman pods.

## 🚨 Critical Rules - READ FIRST

1. **ALWAYS check docs/PRINCIPLES.md** before starting work
2. **Return values matter**: Methods must return `True` not `None` for success
3. **Documentation first**: Check official service docs before complex debugging
4. **Use stdout/stderr** for container logging, not files

## 🎯 Current Development Focus

- **Active Implementation**: Python unified (`implementations/python-unified/`)
- **Stable Implementation**: Shell-based (`implementations/shell-based/`)
- **Goal**: Better debugging, templating, and maintainability

## 🔧 Quick Commands

```bash
# Build containers
make build IMPL=python-unified

# Deploy pod (development mode with host mounts)
make deploy IMPL=python-unified

# View logs
podman logs podserve-simple-apache
podman logs podserve-simple-mail
podman logs podserve-simple-dns

# Run tests
make test

# Debug failing service
podman run --rm -e LOG_LEVEL=DEBUG localhost/podserve-mail:latest mail
```

## 📁 Key Files and Patterns

### Service Implementation Pattern
```python
class MailService(BaseService):
    def configure(self) -> bool:
        # Render templates
        # Return True on success, False on failure
        
    def start_processes(self) -> bool:
        # Start service processes
        # CRITICAL: Return True, not None!
        
    def run_subprocess(self, command: List[str]) -> bool:
        result = subprocess.run(command, capture_output=True)
        if result.returncode != 0:
            self.logger.error(f"Command failed: {' '.join(command)}")
            return False
        return True  # NOT None!
```

### Common Issues

1. **"Service configuration failed"** → Check return values (None vs True)
2. **SSL certificate errors** → Check service syntax (Dovecot needs `<` prefix)
3. **Template failures** → Verify all variables defined in context
4. **Container won't start** → Enable DEBUG logging and check manually

## 🏗️ Architecture Overview

- **Pod Network**: All containers share localhost
- **Volumes**: Separate for web, mail, certificates
- **Services**: Apache (80/443), Mail (25/587/143/993), DNS (53)
- **Health Checks**: HTTP for web, port checks for mail/DNS

## 📚 Documentation Structure

1. **Start Here**: [QUICKSTART.md](../QUICKSTART.md)
2. **Core Principles**: [docs/PRINCIPLES.md](../docs/PRINCIPLES.md)
3. **Podman Patterns**: [docs/PODMAN-BEST-PRACTICES.md](../docs/PODMAN-BEST-PRACTICES.md)
4. **Permissions**: [docs/PERMISSIONS-GUIDE.md](../docs/PERMISSIONS-GUIDE.md)
   - **Developer Friendly**: [docs/DEVELOPER-FRIENDLY-PERMISSIONS.md](../docs/DEVELOPER-FRIENDLY-PERMISSIONS.md)
   - **Namespace Comparison**: [docs/USER-NAMESPACE-COMPARISON.md](../docs/USER-NAMESPACE-COMPARISON.md)
5. **Service Development**: [docs/SERVICE-DEVELOPMENT-GUIDE.md](../docs/SERVICE-DEVELOPMENT-GUIDE.md)
6. **Debugging**: [docs/DEBUGGING-GUIDE.md](../docs/DEBUGGING-GUIDE.md)

## ⚡ Development Workflow

1. Make changes to Python code in `src/podserve/`
2. Changes reflect immediately (host mount in dev mode)
3. Check logs: `podman logs -f podserve-simple-[service]`
4. Debug issues: Set `LOG_LEVEL=DEBUG`
5. Run tests: `make test`

## 🚩 Red Flags to Watch For

- Generic error messages without details
- Missing debug output despite DEBUG level
- Commands that work manually but fail in service
- Services restarting repeatedly
- Health checks failing without clear errors

Remember: **When in doubt, check the documentation first!**