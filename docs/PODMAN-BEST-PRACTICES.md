# Podman Best Practices for PodServe

This document captures Podman-specific learnings and best practices for developing containerized services.

## 🏗️ Pod Architecture

### Pod Networking
- All containers in a pod share the same network namespace
- Containers communicate via `localhost` (not container names)
- External access through pod's port mappings
- DNS resolution shared across all containers

### Pod Structure Example
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: podserve-simple
spec:
  hostname: lab.sethlakowske.com
  containers:
    - name: apache
      # Listens on localhost:80, localhost:443
    - name: mail  
      # Listens on localhost:25, localhost:587, etc.
    - name: dns
      # Listens on localhost:53
```

### Service Discovery Within Pods
```python
# Correct - containers share network namespace
smtp_connection = smtplib.SMTP('localhost', 25)

# Wrong - no container-to-container DNS
smtp_connection = smtplib.SMTP('mail', 25)  # ❌
```

## 📦 Volume Management

### Volume Strategy
1. **Separate volumes by purpose**:
   - `podserve-certificates` - SSL/TLS certificates (shared read-only)
   - `podserve-web` - Web content and data
   - `podserve-mail` - Mail storage
   - `podserve-config` - Configuration files

2. **Volume Mount Patterns**:
```yaml
volumes:
  - name: certificates
    persistentVolumeClaim:
      claimName: podserve-certificates
      
containers:
  - name: apache
    volumeMounts:
      - name: certificates
        mountPath: /data/state/certificates
        readOnly: true  # Read-only for security
```

3. **Development vs Production Volumes**:
```yaml
# Development - host mounts for live editing
volumes:
  - name: source-code
    hostPath:
      path: ./src/podserve
      
# Production - only persistent volumes
volumes:
  - name: web-data
    persistentVolumeClaim:
      claimName: podserve-web
```

## 🔧 Development Workflow

### Quick Iteration Setup
1. **Create dev.yaml** with host mounts:
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

2. **Use same paths** in dev and prod:
- Development: Host directory mounted to `/opt/podserve`
- Production: Code copied to `/opt/podserve`
- Services always use `/opt/podserve` - no switching needed

### Building Images
```bash
# Build single service
cd docker && ./build.sh apache

# Build all services
cd docker && ./build.sh all

# Tag consistently
podman tag podserve-apache:latest localhost/podserve-apache:latest
```

### Deployment Commands
```bash
# Deploy pod
podman play kube simple.yaml

# Deploy with host networking (development)
podman play kube --network host dev.yaml

# Remove pod and volumes
podman play kube --down simple.yaml

# Remove pod but keep volumes
podman pod rm -f podserve-simple
```

## 🐛 Container Debugging

### Essential Debugging Commands
```bash
# View all containers in pod
podman pod ps
podman ps --pod

# Check container logs
podman logs podserve-simple-apache
podman logs -f podserve-simple-mail  # Follow logs

# Execute commands in running container
podman exec -it podserve-simple-apache bash
podman exec podserve-simple-mail dovecot -n  # Check config

# Inspect pod networking
podman pod inspect podserve-simple

# Check volume mounts
podman inspect podserve-simple-apache | grep -A10 Mounts
```

### Health Check Debugging
```bash
# Check health status
podman healthcheck run podserve-simple-apache

# View health check logs
podman events --filter event=health_status

# Manual health check
podman exec podserve-simple-apache curl -f http://localhost/ || echo "Failed"
```

## 🚀 Performance Optimization

### Image Building
1. **Use multi-stage builds**:
```dockerfile
# Build stage
FROM debian:12-slim as builder
RUN apt-get update && apt-get install -y build-tools

# Runtime stage  
FROM debian:12-slim
COPY --from=builder /built/files /app/
```

2. **Layer caching strategies**:
```dockerfile
# Install dependencies first (changes less often)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy source code last (changes frequently)
COPY src/ .
```

3. **Minimize layer count**:
```dockerfile
# Good - single layer
RUN apt-get update && apt-get install -y \
    package1 package2 package3 \
    && rm -rf /var/lib/apt/lists/*

# Bad - multiple layers
RUN apt-get update
RUN apt-get install -y package1
RUN apt-get install -y package2
```

### Runtime Performance
1. **Container startup order** - No dependencies in pod spec, handle in apps
2. **Resource limits** - Set appropriate CPU/memory limits
3. **Shared memory** - Increase `/dev/shm` size if needed

## 🔒 Security Best Practices

### User Management
```dockerfile
# Create non-root user
RUN useradd -m -s /bin/bash appuser

# Switch to non-root user
USER appuser

# For services requiring root (mail, DNS)
USER root
# But drop privileges in the application when possible
```

### Network Security
1. **Minimize exposed ports** - Only expose what's needed
2. **Use pod network isolation** - Internal services on localhost only
3. **Read-only root filesystem** where possible:
```yaml
securityContext:
  readOnlyRootFilesystem: true
```

### Secret Management
```bash
# Create secrets
podman secret create ssl-cert ./cert.pem
podman secret create ssl-key ./key.pem

# Use in pod
podman play kube --secret ssl-cert,ssl-key simple.yaml
```

## 📊 Monitoring and Logging

### Centralized Logging
```yaml
# All containers log to stdout/stderr
# View all pod logs
podman pod logs podserve-simple

# Filter by container
podman logs podserve-simple-apache
```

### Resource Monitoring
```bash
# Real-time stats
podman stats --no-stream

# Pod resource usage
podman pod stats podserve-simple

# System events
podman events --filter pod=podserve-simple
```

## 🎯 Common Patterns

### Init Container Pattern
```yaml
initContainers:
  - name: setup
    image: localhost/podserve-base
    command: ["/scripts/setup.sh"]
    volumeMounts:
      - name: shared-data
        mountPath: /data
```

### Sidecar Pattern
```yaml
containers:
  - name: main-app
    image: localhost/podserve-apache
  - name: log-forwarder
    image: localhost/log-forwarder
    # Shares pod network, can read logs
```

### Configuration Reloading
```bash
# Reload without restart
podman exec podserve-simple-apache apache2ctl graceful
podman exec podserve-simple-mail postfix reload
podman exec podserve-simple-dns rndc reload
```

## ⚠️ Common Pitfalls

### 1. Volume Permission Issues
- Containers may run as different users
- Set permissions appropriately in Dockerfile
- Use init containers for setup if needed

### 2. Port Conflicts
- All containers share network namespace
- Each service must use different ports
- Check for conflicts before deployment

### 3. Pod Network Limitations
- No individual container DNS names
- All traffic via localhost
- External DNS resolution might need configuration

### 4. Resource Constraints
- Pods share cgroups limits
- Individual container limits are guidelines
- Monitor actual usage vs. limits

## 💡 Tips and Tricks

### Quick Development Cycle
```bash
# Alias for common operations
alias pod-rebuild='cd docker && ./build.sh all && cd .. && podman play kube --down simple.yaml && podman play kube simple.yaml'

# Watch logs during development
watch -n 1 'podman ps --pod'

# Clean up everything
podman pod rm -f podserve-simple && podman volume prune -f
```

### Debugging Checklist
1. ✅ Check pod is running: `podman pod ps`
2. ✅ Check all containers: `podman ps --pod`
3. ✅ Check logs: `podman logs <container>`
4. ✅ Check networking: `podman pod inspect`
5. ✅ Check volumes: `podman volume ls`
6. ✅ Check health: `podman healthcheck run`

Remember: Podman pods follow Kubernetes semantics, making them portable to k8s environments.