# Architecture Decisions

This document captures key architectural decisions made in PodServe and the reasoning behind them.

## 🏗️ Multi-Container Pod vs Single Container

### Decision: Multi-Container Pod Architecture

We chose to run each service (Apache, Mail, DNS) in separate containers within a Podman pod.

**Rationale:**
- **Service isolation**: Failures in one service don't affect others
- **Independent updates**: Can update mail server without touching web server
- **Resource management**: Per-service CPU/memory limits
- **Better debugging**: Separate logs and processes
- **Industry standard**: Aligns with Kubernetes patterns

**Trade-offs:**
- More complex initial setup
- Multiple Dockerfiles to maintain
- Higher memory usage (duplicate libraries)
- Volume permission coordination needed

**Alternative Considered:** All-in-one container with supervisor
- Simpler but less flexible
- See [CONTAINER-COMPARISON.md](../shared/docs/CONTAINER-COMPARISON.md) for detailed analysis

## 🐍 Python Framework vs Shell Scripts

### Decision: Python-based Service Framework

Moved from shell-based configuration to Python framework with Jinja2 templates.

**Rationale:**
- **Better error handling**: Exceptions vs exit codes
- **Template support**: Jinja2 for complex configurations
- **Debugging**: Proper logging and stack traces
- **Testability**: Unit tests for service logic
- **Maintainability**: Object-oriented design

**Implementation Approach:**
```python
# Base service class for all services
class BaseService(ABC):
    def configure(self) -> bool
    def start_processes(self) -> bool
    def health_check(self) -> bool
```

**Trade-offs:**
- Python dependency in containers
- Slightly larger image sizes
- Learning curve for contributors

## 📁 Configuration Management

### Decision: Environment Variables + Templates

Configuration flows from environment variables through Jinja2 templates to service configs.

**Rationale:**
- **12-factor app**: Environment-based configuration
- **Flexibility**: Complex logic in templates
- **Validation**: Can validate before writing
- **Reusability**: Share template snippets
- **Debugging**: Can output rendered templates

**Example Flow:**
```
Environment Variable → Python ConfigManager → Jinja2 Template → Service Config File
DOMAIN=example.com → config.domain → {{ domain }} → ServerName example.com
```

**Trade-offs:**
- Template complexity can grow
- Additional rendering step
- Need to manage template versions

## 🔌 Service Communication

### Decision: Localhost within Pod Network

All inter-service communication uses localhost (shared pod network namespace).

**Rationale:**
- **Simplicity**: No service discovery needed
- **Performance**: No network overhead
- **Security**: No external exposure needed
- **Standard**: Kubernetes pod networking model

**Example:**
```python
# Mail service connects to local DNS
resolver = dns.resolver.Resolver()
resolver.nameservers = ['127.0.0.1']

# Apache connects to local mail
smtp = smtplib.SMTP('localhost', 25)
```

**Trade-offs:**
- Can't scale services independently
- Port conflicts need careful management
- No load balancing between services

## 📊 Logging Strategy

### Decision: Dual Logging (stdout + files)

Services log to both stdout/stderr and files in development.

**Rationale:**
- **Container native**: stdout for `podman logs`
- **Debugging**: Files for in-container debugging
- **Development**: Easy log access during development
- **Production**: Can disable file logging

**Implementation:**
```python
# Console for container logs
console_handler = logging.StreamHandler(sys.stdout)

# File for debugging (development only)
if debug_mode:
    file_handler = logging.FileHandler('/data/logs/service.log')
```

**Trade-offs:**
- Duplicate log entries in development
- Need to manage log rotation
- Extra I/O in development mode

## 🏃 Development Workflow

### Decision: Host-Mounted Source Code

Development mode mounts host source code into containers.

**Rationale:**
- **Fast iteration**: No rebuild for code changes
- **IDE integration**: Edit with preferred tools
- **Debugging**: Can modify code while running
- **Same paths**: Dev and prod use same paths

**Setup:**
```yaml
# dev.yaml
volumes:
  - name: source
    hostPath:
      path: ./src/podserve
containers:
  - volumeMounts:
    - name: source
      mountPath: /opt/podserve
```

**Trade-offs:**
- Need separate dev and prod configs
- File permission issues possible
- Can't test final image behavior

## 🔒 Security Model

### Decision: Service-Specific Users Where Possible

Run services as non-root when feasible, root when required.

**Rationale:**
- **Least privilege**: Minimize root usage
- **Compatibility**: Some services need root
- **Practical**: Balance security and functionality

**Implementation:**
- Apache: Runs as www-data after binding ports
- Mail: Requires root for port 25 binding
- DNS: Requires root for port 53 binding
- Certbot: Needs root for certificate management

**Trade-offs:**
- Inconsistent user model
- Some services must run as root
- Complex permission management

## 🧪 Testing Strategy

### Decision: Shared Test Suite

Single test suite works across all implementations.

**Rationale:**
- **Consistency**: Same behavior expected
- **Efficiency**: Write tests once
- **Validation**: Ensures compatibility
- **Refactoring**: Safe to change implementations

**Structure:**
```
shared/tests/
├── test_apache_integration.py
├── test_mail_integration.py
├── test_dns_integration.py
└── test_pod_integration.py
```

**Trade-offs:**
- Tests must be implementation-agnostic
- Can't test implementation-specific features
- Slower test runs (test all implementations)

## 🚀 Build Strategy

### Decision: Local Multi-Stage Builds

Build images locally using multi-stage Dockerfiles.

**Rationale:**
- **Control**: Full control over build process
- **Caching**: Leverage layer caching
- **Flexibility**: Easy to customize
- **Debugging**: Can inspect build stages

**Pattern:**
```dockerfile
# Build stage - compile/prepare
FROM debian:12-slim as builder
# ... build steps ...

# Runtime stage - minimal image
FROM debian:12-slim
COPY --from=builder /built/app /app
```

**Trade-offs:**
- No registry/CI integration by default
- Manual version management
- Local storage requirements

## 🎯 Design Principles

### Principle 1: Fail Fast and Loud
Services should fail immediately with clear errors rather than limping along.

### Principle 2: Explicit Over Implicit
Configuration should be explicit (environment variables) not magic.

### Principle 3: Development Mirrors Production
Same code paths, same directory structures, same entry points.

### Principle 4: Compose Over Inherit
Services compose base functionality rather than complex inheritance.

### Principle 5: Test in Isolation
Each service must be testable independently before integration.

## 📈 Future Considerations

### Potential Improvements

1. **Service Mesh**: Add Envoy/Istio for advanced networking
2. **Orchestration**: Full Kubernetes deployment options
3. **Monitoring**: Prometheus metrics endpoints
4. **Secrets Management**: HashiCorp Vault integration
5. **Multi-Architecture**: ARM64 support for RPi deployment

### Decisions to Revisit

1. **Single Pod**: May need multiple pods for scaling
2. **Root Services**: Investigate rootless alternatives
3. **Python Framework**: Consider Go for smaller images
4. **Local Builds**: May need CI/CD pipeline

## 🤔 Lessons Learned

1. **Start simple**: Shell scripts were fine initially
2. **Evolve gradually**: Python framework added when needed
3. **Document decisions**: This file helps future developers
4. **Test everything**: Saved countless hours
5. **Community standards**: Following Podman/K8s patterns helps

Remember: Architecture is about trade-offs. These decisions made sense for our use case but may not for yours.