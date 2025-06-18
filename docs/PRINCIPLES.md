# Core Development Principles

This document contains the most critical principles learned from developing PodServe. **Read this first** before starting any implementation work.

## 🚨 Critical Principles (Check These First!)

### 1. Documentation-First Debugging
**ALWAYS** consult official service documentation before attempting complex troubleshooting.

**Real Example - Dovecot SSL Configuration:**
- **Problem**: SSL context initialization failing with "Can't load SSL certificate"
- **Time Wasted**: Hours troubleshooting permissions, formats, ciphers
- **Actual Issue**: Missing `<` prefix in Dovecot config syntax
- **Solution**: `ssl_cert = <${SSL_CERT_FILE}` (not `ssl_cert = ${SSL_CERT_FILE}`)

**Key Takeaway**: The `<` tells Dovecot to read from file vs. expecting inline content. This basic syntax is documented clearly in Dovecot docs.

### 2. Return Value Handling ⚠️
**ALWAYS** verify return types match expected boolean patterns.

**Most Common Bug Pattern:**
```python
def run_subprocess(self, command: List[str]) -> bool:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        self.logger.error(f"Command failed: {' '.join(command)}")
        return False
    # CRITICAL: Must return True, not None!
    return True  # ✅ CORRECT
    # return None  # ❌ WRONG - causes silent failures
```

**Why This Matters:**
- Service code uses `if not self.run_subprocess([...]):` patterns
- `None` is falsy but not the same as `False`
- Leads to mysterious "Service configuration failed" with no errors

### 3. Container Logging Best Practices
**ALWAYS** configure services to log to stdout/stderr.

**Principles:**
- Containers should log to stdout/stderr, not files
- Use service-specific methods to redirect logs
- Test with `podman logs <container>` to verify
- Remove log volume mounts when implementing proper logging

**Example - Apache:**
```apache
ErrorLog /dev/stderr
CustomLog /dev/stdout combined
```

### 4. Volume Permissions and Multi-Container Coordination ⚠️
**ALWAYS** plan volume permissions before deployment when containers share volumes.

**Critical Issue**: Different containers run as different users (Apache as www-data, Mail as root, etc.) and can't access each other's files by default.

**Example Problem:**
```bash
# Apache creates file as www-data (UID 33)
-rw-r--r-- 1 www-data www-data /data/web/file.txt

# Mail service (running as root) can read but not write
# Other services running as different users may not even be able to read!
```

**Solutions:**
1. **Use init containers** to set up permissions
2. **Create common groups** across containers
3. **Set appropriate umask** in services
4. **Plan permission strategy** before implementation

**Key Decision**: We use explicit UID/GID management rather than user namespace remapping because:
- Mail and DNS services require privileged ports (< 1024)
- User namespace remapping cannot bind to privileged ports
- Network performance penalty (30-50%) is unacceptable for web services
- Explicit permission management is simpler to debug and understand

See [Permissions Guide](PERMISSIONS-GUIDE.md) and [User Namespace Comparison](USER-NAMESPACE-COMPARISON.md) for detailed analysis.

## 🏗️ Architecture Principles

### 1. Service Isolation
- One service per container (Apache, Mail, DNS separate)
- Shared pod network for inter-service communication
- Service-specific volumes for data isolation

### 2. Configuration Management
- Use environment variables for deployment-specific settings
- Template-driven configuration with Jinja2
- Validate configurations at startup, fail fast
- Keep reference configurations for comparison

### 3. Build Strategy
- Base image with common utilities and health checks
- Service-specific images built on base
- Multi-stage builds for smaller production images
- Development builds with debugging tools included

## 🧪 Testing & Debugging Principles

### 1. Isolation-First Development Strategy
**ALWAYS** develop services individually before integration.

**Critical Pattern**: Build each service in complete isolation, validate thoroughly, then integrate systematically:
1. **Phase 1**: Plan service requirements and success criteria
2. **Phase 2**: Develop service in isolation with comprehensive testing
3. **Phase 3**: Establish performance baselines and validate against targets
4. **Phase 4**: Plan integration strategy with existing services
5. **Phase 5**: Combine services systematically (pairs, then triplets)
6. **Phase 6**: Production readiness validation

See [Service Development Guide](SERVICE-DEVELOPMENT-GUIDE.md) for detailed methodology.

### 2. Progressive Testing Strategy
Test in this order:
1. **Service instantiation** - Can the service class be created?
2. **Configuration rendering** - Do templates render correctly?
3. **Process execution** - Do commands run successfully?
4. **Health checks** - Does the service report healthy?
5. **Integration** - Does it work with other services?

### 3. Debugging Methodology
When a service fails:
1. **Enable DEBUG logging** first
2. **Check return values** (especially None vs bool)
3. **Test commands manually** in the container
4. **Verify file permissions** and paths
5. **Compare with reference** configurations

### 4. Logging Strategy
```python
# Service level - major operations
self.logger.info("Starting service configuration")

# Method level - function entry/exit
self.logger.debug("Rendering template: main.conf")

# Command level - subprocess execution
self.logger.info(f"Running command: {' '.join(command)}")

# Result level - command output
if result.stdout:
    self.logger.debug(f"Output: {result.stdout}")
if result.stderr:
    self.logger.warning(f"Stderr: {result.stderr}")
```

## 📦 Container Best Practices

### 1. Dockerfile Patterns
```dockerfile
# Consistent base image
FROM localhost/podserve-base:latest

# Switch to root for system operations
USER root

# Install packages and clean up
RUN apt-get update && apt-get install -y \
    package1 package2 \
    && rm -rf /var/lib/apt/lists/*

# Create required directories
RUN mkdir -p /data/{config,logs,state} \
    && chown -R root:root /data

# Set appropriate user for runtime
USER service-user  # or stay root if required
```

### 2. Health Check Implementation
- Use simple, fast checks (HTTP GET, port connection)
- Implement both liveness and readiness where applicable
- Fail fast with clear error messages
- Log health check failures for debugging

### 3. Volume Management
- Separate volumes for config, data, and state
- Use read-only mounts where possible (certificates)
- Document volume purposes and ownership requirements
- Test with both empty and pre-populated volumes

## 🔧 Development Workflow Principles

### 1. Rapid Iteration
- Use host-mounted volumes in development
- Avoid rebuilding images for code changes
- Keep production and development paths identical
- Use the same tooling in dev and prod

### 2. Error Handling
- Fail fast with clear error messages
- Log enough context to debug issues
- Validate inputs before processing
- Handle signals gracefully (SIGTERM, SIGINT)

### 3. Performance Considerations
- Cache rendered templates when possible
- Minimize subprocess calls
- Use connection pooling for databases
- Monitor resource usage in health checks

## 📝 Documentation Principles

### 1. Document Failures
When you encounter an issue:
- Document the symptom
- Document what you tried
- Document the actual solution
- Extract the general principle

### 2. Keep Examples Real
- Use actual error messages
- Show real configuration snippets
- Include timestamps and context
- Reference specific files/lines

### 3. Maintain Hierarchy
- Universal principles go here
- Implementation-specific lessons in their directories
- Service-specific patterns in service docs
- Debugging patterns in debugging guide

## 🎯 Success Indicators

You're on the right track when:
- Services start and stay running
- Health checks pass consistently
- Logs show clear execution flow
- Integration tests pass
- Container restarts recover cleanly

## 🚩 Red Flags

Watch out for these warning signs:
- Generic "configuration failed" messages
- Missing debug output despite DEBUG level
- Commands work manually but fail in service
- Templates render but don't work
- Services restart repeatedly

## 💡 Key Insights

1. **Infrastructure code needs software engineering discipline** - testing, logging, abstractions
2. **Official documentation saves hours** - always check it first
3. **Return values matter** - None vs False vs True affects control flow
4. **Fail fast and loud** - silent failures waste debugging time
5. **Templates are code** - test them like code

Remember: Every hour spent establishing good patterns saves days of debugging later.