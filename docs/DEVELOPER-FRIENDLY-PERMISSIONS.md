# Developer-Friendly Permission Strategy

This guide outlines a permission strategy that makes containers use the developer's UID/GID by default, simplifying volume management and file access during development.

## 🎯 Goal

Make all containers run as UID/GID 1000 (matching typical developer user) by default, with your group having access to files created by service-specific users when necessary.

## 🏗️ Implementation Strategy

### 1. Base Image Configuration

Create a base image that sets up the developer user as default:

```dockerfile
# base/Dockerfile
FROM debian:12-slim

# Create developer user matching host UID/GID
ARG USER_UID=1000
ARG USER_GID=1000
ARG USERNAME=developer

# Create group and user
RUN groupadd -g ${USER_GID} ${USERNAME} && \
    useradd -u ${USER_UID} -g ${USER_GID} -m -s /bin/bash ${USERNAME}

# Create common directories with developer ownership
RUN mkdir -p /data/{config,logs,state,web,mail} && \
    chown -R ${USER_UID}:${USER_GID} /data

# Install sudo for cases where root is needed
RUN apt-get update && apt-get install -y sudo && \
    echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    rm -rf /var/lib/apt/lists/*

# Set default user
USER ${USERNAME}
WORKDIR /home/${USERNAME}

# But allow running as root if needed
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
```

### 2. Smart Entrypoint Script

Create an entrypoint that handles both development and production modes:

```bash
#!/bin/bash
# docker-entrypoint.sh

# If running as root (production mode)
if [ "$(id -u)" = "0" ]; then
    # Ensure developer group exists
    groupadd -g 1000 developer 2>/dev/null || true
    
    # Add service users to developer group if they exist
    for user in www-data mail dovecot postfix bind; do
        if id "$user" &>/dev/null; then
            usermod -a -G developer "$user" 2>/dev/null || true
        fi
    done
    
    # Set umask so group can write
    umask 002
    
    # Fix permissions on data directories
    chgrp -R developer /data 2>/dev/null || true
    chmod -R g+rwX /data 2>/dev/null || true
fi

# Execute the actual command
exec "$@"
```

### 3. Service-Specific Dockerfiles

#### Apache Example

```dockerfile
FROM localhost/podserve-base:latest

# Switch to root for installation
USER root

# Install Apache
RUN apt-get update && apt-get install -y apache2 && \
    rm -rf /var/lib/apt/lists/*

# Add www-data to developer group
RUN usermod -a -G developer www-data

# Configure Apache to respect group permissions
RUN echo "umask 002" >> /etc/apache2/envvars

# Copy entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Default to developer user
USER developer

# But Apache needs to start as root to bind ports
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["sudo", "apache2ctl", "-D", "FOREGROUND"]
```

#### Mail Example (Requires Root)

```dockerfile
FROM localhost/podserve-base:latest

USER root

# Install mail services
RUN apt-get update && apt-get install -y postfix dovecot-imapd && \
    rm -rf /var/lib/apt/lists/*

# Ensure mail users are in developer group
RUN usermod -a -G developer postfix && \
    usermod -a -G developer dovecot

# Configure services to create files with group write permissions
RUN echo "umask = 0002" >> /etc/dovecot/conf.d/10-mail.conf && \
    postconf -e "umask = 002"

# Mail services must run as root
USER root

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/usr/local/bin/start-mail.sh"]
```

### 4. Pod Configuration for Development

```yaml
# dev.yaml
apiVersion: v1
kind: Pod
metadata:
  name: podserve-dev
spec:
  # Set security context at pod level
  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    fsGroupChangePolicy: "OnRootMismatch"
  
  containers:
  - name: apache
    image: localhost/podserve-apache:latest
    securityContext:
      runAsUser: 1000  # Override to run as developer
      capabilities:
        add:
          - NET_BIND_SERVICE  # Allow binding to ports < 1024
    volumeMounts:
    - name: data
      mountPath: /data
      
  - name: mail
    image: localhost/podserve-mail:latest
    securityContext:
      runAsUser: 0  # Mail needs root
      runAsGroup: 0
    volumeMounts:
    - name: data
      mountPath: /data
      
  - name: dns
    image: localhost/podserve-dns:latest
    securityContext:
      runAsUser: 1000
      capabilities:
        add:
          - NET_BIND_SERVICE
    volumeMounts:
    - name: data
      mountPath: /data
      
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: podserve-data
```

### 5. Alternative: User Namespace Remapping

Configure Podman to automatically map container users to your UID using user namespaces:

```bash
# Setup subuid/subgid (one-time)
echo "seth:100000:65536" | sudo tee -a /etc/subuid
echo "seth:100000:65536" | sudo tee -a /etc/subgid

# ~/.config/containers/containers.conf
[containers]
  userns = "keep-id:uid=1000,gid=1000"

# Use with volume mounts
podman run --userns=keep-id \
  -v /home/seth/data:/data:z,U \
  container-image
```

**⚠️ Important Limitations for PodServe:**
- **Cannot bind privileged ports** (< 1024): Mail (port 25) and DNS (port 53) won't work
- **30-50% network performance penalty** due to slirp4netns networking
- **Volume mounting slower** due to `:U` flag ownership changes
- **Complex debugging** when permission issues occur

**Recommendation**: Use explicit UID/GID approach for PodServe due to privileged port requirements.

See [USER-NAMESPACE-COMPARISON.md](USER-NAMESPACE-COMPARISON.md) for detailed analysis.

### 6. Build-time Arguments Approach

Make UID/GID configurable at build time:

```dockerfile
# Dockerfile
ARG USER_UID=1000
ARG USER_GID=1000

FROM debian:12-slim

# Use build args
RUN groupadd -g ${USER_GID} appuser && \
    useradd -u ${USER_UID} -g ${USER_GID} -m appuser

USER appuser
```

Build with:
```bash
# Build with your UID/GID
podman build --build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g) -t myimage .
```

## 🛠️ Makefile Integration

Update the Makefile to handle UID/GID:

```makefile
# Makefile
USER_UID ?= $(shell id -u)
USER_GID ?= $(shell id -g)

.PHONY: build-dev
build-dev:
	@echo "Building with UID=$(USER_UID) GID=$(USER_GID)"
	cd docker && ./build.sh all --build-arg USER_UID=$(USER_UID) --build-arg USER_GID=$(USER_GID)

.PHONY: deploy-dev
deploy-dev:
	# Use development pod spec with user mappings
	podman play kube dev.yaml
	
.PHONY: fix-permissions
fix-permissions:
	# Fix permissions on existing volumes
	podman run --rm -v podserve-data:/data alpine chown -R $(USER_UID):$(USER_GID) /data
```

## 📝 Service Configuration Updates

### Apache Configuration

```apache
# apache.conf
# Run Apache workers as developer user when possible
<IfModule unixd_module>
    User ${APACHE_RUN_USER}
    Group developer
</IfModule>

# Set umask for created files
# This goes in envvars or startup script
umask 002
```

### Postfix Configuration

```bash
# main.cf additions
# Make postfix create files with group permissions
umask = 002

# Use developer group for mail
mail_owner = postfix
setgid_group = developer
```

### Python Service Updates

```python
# In BaseService.__init__
import os
import grp

class BaseService:
    def __init__(self, service_name: str, debug: bool = False):
        super().__init__(service_name, debug)
        
        # Ensure group permissions for created files
        os.umask(0o002)
        
        # If running as root, ensure files are group-accessible
        if os.getuid() == 0:
            try:
                developer_gid = grp.getgrnam('developer').gr_gid
                os.setgid(developer_gid)
            except KeyError:
                self.logger.warning("Developer group not found")
```

## 🎯 Benefits of This Approach

1. **Development Simplicity**
   - Files created in containers are owned by your user
   - Easy to edit/manage files on host
   - No permission issues when mounting host directories

2. **Production Compatibility**
   - Services can still run as root when needed
   - Group permissions ensure access across users
   - Umask settings maintain group write permissions

3. **Debugging Ease**
   - Can directly access all container-created files
   - No need for sudo to view logs or configs
   - IDE file watchers work properly

## ⚡ Quick Implementation Steps

1. **Update Base Image**
```bash
# Add to base/Dockerfile
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd -g ${USER_GID} developer && \
    useradd -u ${USER_UID} -g ${USER_GID} -m developer
```

2. **Modify Service Images**
```bash
# Add to each service
RUN usermod -a -G developer www-data  # or other service user
USER developer  # When possible
```

3. **Update Build Script**
```bash
# docker/build.sh
BUILD_ARGS="--build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g)"
podman build $BUILD_ARGS -t localhost/podserve-base:latest base/
```

4. **Configure Services**
- Set umask 002 in all services
- Add service users to developer group
- Configure services to respect group permissions

## 🚨 Important Considerations

1. **Security**: This approach is for development. Production should use proper user isolation.

2. **Port Binding**: Services running as non-root need capabilities to bind to privileged ports (<1024).

3. **Service Requirements**: Some services absolutely require root (mail on port 25).

4. **File Ownership**: Existing files may need permission fixes after implementing this.

## 📋 Migration Checklist

- [ ] Update base Dockerfile with developer user
- [ ] Add entrypoint script for permission handling  
- [ ] Modify each service Dockerfile
- [ ] Update build scripts with UID/GID args
- [ ] Configure services for group permissions (umask)
- [ ] Test file creation and access
- [ ] Update documentation
- [ ] Fix permissions on existing volumes

This approach balances developer convenience with service requirements, making local development much smoother while maintaining the ability to run services properly in production.