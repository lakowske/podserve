# Podman Permissions and UID/GID Guide

This guide explains the complex world of user IDs, group IDs, and file permissions in Podman containers, particularly when containers need to share volumes.

## 🔑 Understanding the Problem

When multiple containers in a pod share volumes, permission issues arise because:
- Each container may run as a different user
- Volume ownership is set when first created
- Containers can't change ownership of files they don't own
- Podman doesn't automatically handle permission coordination
- **CRITICAL**: Default user namespace mapping causes volume mount failures

## ⭐ VOLUME MOUNT SOLUTION (CRITICAL FOR ALL SERVICES)

**ISSUE DISCOVERED**: Containers cannot write to host-mounted volumes despite correct UID/GID configuration.

```bash
# ❌ THIS FAILS - Permission denied
podman run -v ./data:/data/state/certificates service-image

# ✅ THIS WORKS - Preserves user namespace
podman run --userns=keep-id -v ./data:/data/state/certificates:Z service-image
```

### Root Cause
Podman's default user namespace mapping causes mounted directories to appear as `root:root` inside the container, even when they're owned by the developer (`seth:seth`) on the host.

### Solution Components
1. `--userns=keep-id` - Preserves host user ID mapping inside container
2. `:Z` - Sets proper SELinux context for mounted volume
3. Container built with host UID/GID (1000:1000)

### Implementation Pattern
```yaml
# In Kubernetes/Podman pod specs
containers:
- name: service
  image: localhost/podserve-harmony-service:latest
  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
  volumeMounts:
  - name: service-data
    mountPath: /data/state/service

# With podman command additions
podmanArgs:
- --userns=keep-id
```

**APPLIES TO**: ALL services requiring persistent volume storage

## 📊 How UIDs/GIDs Work in Containers

### Container User Mapping

```bash
# Host system
$ id
uid=1000(seth) gid=1000(seth)

# Inside container (running as root)
$ podman exec container-name id
uid=0(root) gid=0(root)

# Inside container (running as www-data)
$ podman exec apache-container id  
uid=33(www-data) gid=33(www-data)
```

### The UID Namespace Problem

By default, Podman runs containers with the same UIDs as inside the container:
- Container root (UID 0) = Host root (UID 0)
- Container www-data (UID 33) = Host UID 33
- This means containers with different UIDs can't share files!

## 🔍 Real-World Examples from PodServe

### Example 1: Certificate Sharing

**Problem**: Apache (www-data) and Mail (root) need to read SSL certificates

```bash
# Certificate volume owned by root
$ ls -la /data/state/certificates/
-rw-r----- 1 root root cert.pem
-rw------- 1 root root key.pem

# Apache running as www-data can't read!
```

**Solution**: Make certificates world-readable (for cert) or use group permissions

```dockerfile
# In the container that creates certificates
RUN chmod 644 /data/state/certificates/cert.pem && \
    chmod 640 /data/state/certificates/key.pem && \
    chgrp www-data /data/state/certificates/key.pem
```

### Example 2: Shared Configuration Directory

**Problem**: Multiple services need to write to config directory

```bash
# Initial state - created by first container (root)
$ ls -la /data/
drwxr-xr-x 2 root root config/

# Apache (www-data) can't write configs!
```

**Solution**: Create with appropriate permissions upfront

```dockerfile
# In base image or init container
RUN mkdir -p /data/config && \
    chmod 777 /data/config  # Or use ACLs for better security
```

### Example 3: Mail Storage Permissions

**Problem**: Postfix (root) creates mail, Dovecot (dovecot user) needs to read

```bash
# Mail created by Postfix
-rw------- 1 root root /var/mail/user@domain/new/message

# Dovecot can't read!
```

**Solution**: Configure services to use same UID/GID

```dockerfile
# Make both services use mail group
RUN groupadd -g 8 mail && \
    usermod -a -G mail postfix && \
    usermod -a -G mail dovecot
```

## 🛠️ Solutions and Patterns

### 1. Init Container Pattern

Use an init container to set up permissions before services start:

```yaml
apiVersion: v1
kind: Pod
spec:
  initContainers:
  - name: permission-setup
    image: localhost/podserve-base
    command:
    - sh
    - -c
    - |
      # Create directories with correct permissions
      mkdir -p /data/config /data/logs /data/state
      chmod 755 /data/config /data/state
      chmod 777 /data/logs  # All services can write logs
      
      # Set up shared group
      chgrp -R 1000 /data/state  # Shared group GID
    volumeMounts:
    - name: data
      mountPath: /data
```

### 2. Common User/Group Strategy

Create a common group across all containers:

```dockerfile
# In base image
RUN groupadd -g 1000 podserve

# In each service image
RUN usermod -a -G podserve www-data  # Apache
RUN usermod -a -G podserve mail      # Postfix
RUN usermod -a -G podserve dovecot   # Dovecot
```

### 3. Permission Modes for Different Scenarios

```bash
# Read-only shared files (certificates)
-r--r--r-- 1 root root cert.pem      # 444 - Everyone can read

# Shared config (multiple readers, single writer)  
-rw-r--r-- 1 root podserve config    # 644 - Owner writes, group/others read

# Shared data directory (multiple writers)
drwxrwxr-x 2 root podserve data/     # 775 - Owner/group write, others read

# Logs directory (everyone writes)
drwxrwxrwx 2 root root logs/         # 777 - Everyone writes (use carefully)

# Sensitive shared data
-rw-r----- 1 root podserve secret    # 640 - Owner read/write, group read only
```

### 4. Rootless Podman Considerations

When running Podman as non-root user:

```bash
# Host user seth (UID 1000) runs podman
$ podman run --rm alpine id
uid=0(root) gid=0(root)  # But this is actually UID 100000 on host!

# UID mapping for rootless
Container UID 0 → Host UID 100000
Container UID 1 → Host UID 100001
# etc.
```

This adds another layer of complexity for volume permissions!

## 📋 Debugging Permission Issues

### 1. Check Actual Permissions

```bash
# See numeric permissions
$ podman exec container stat -c "%a %u:%g %n" /data/config
755 0:0 /data/config

# See which user is running
$ podman exec container whoami
www-data

# Test file access
$ podman exec container test -r /data/file && echo "Can read" || echo "Cannot read"
```

### 2. Common Permission Errors

```bash
# Permission denied
nginx: [error] open() "/data/logs/error.log" failed (13: Permission denied)

# Cannot create directory
mkdir: cannot create directory '/data/config': Permission denied

# Certificate read failure  
SSL_CTX_use_certificate_file() failed (Permission denied)
```

### 3. Fix Permission Issues

```bash
# From host (if you have access)
$ sudo chown -R 33:33 /var/lib/containers/storage/volumes/podserve-web/_data

# From privileged container
$ podman run --privileged -v podserve-web:/data alpine chown -R 33:33 /data

# Using init container (recommended)
# See init container pattern above
```

## 🏗️ Best Practices

### 1. Plan Permissions Early

Before creating containers, decide:
- Which user will each service run as?
- Which files need to be shared?
- Read-only or read-write access?
- Can we use a common group?

### 2. Document Permission Requirements

```dockerfile
# In Dockerfile comments
# This service runs as www-data (33:33)
# Needs: read access to /data/state/certificates
# Needs: write access to /data/logs
# Creates: files in /data/web owned by www-data
```

### 3. Use Least Privilege

```dockerfile
# Bad - too permissive
RUN chmod -R 777 /data

# Good - specific permissions
RUN chmod 755 /data && \
    chmod 775 /data/shared && \
    chmod 700 /data/private
```

### 4. Test Permission Scenarios

```bash
# Test script for CI/CD
#!/bin/bash
# Test that Apache can read certificates
podman exec podserve-apache test -r /data/state/certificates/cert.pem || exit 1

# Test that Mail can write to shared logs
podman exec podserve-mail touch /data/logs/mail-test || exit 1

# Test that both can read shared config
podman exec podserve-apache cat /data/config/shared.conf > /dev/null || exit 1
podman exec podserve-mail cat /data/config/shared.conf > /dev/null || exit 1
```

## 🎯 PodServe-Specific Solutions

### Certificate Sharing Solution

```dockerfile
# In certbot/base image that creates certs
# Make certs readable by all services
RUN mkdir -p /data/state/certificates && \
    chmod 755 /data/state/certificates

# After creating certificates
CMD certbot ... && \
    chmod 644 /data/state/certificates/*.pem && \
    chmod 600 /data/state/certificates/privkey.pem && \
    chgrp podserve /data/state/certificates/privkey.pem && \
    chmod 640 /data/state/certificates/privkey.pem
```

### Logging Solution

```dockerfile
# Create logs directory that all can write to
RUN mkdir -p /data/logs && \
    chmod 1777 /data/logs  # Sticky bit prevents deletion by others
```

### Web Content Solution  

```dockerfile
# Apache container
RUN mkdir -p /data/web && \
    chown www-data:www-data /data/web
```

## ⚠️ Common Pitfalls

### 1. Volume Ownership Persistence

```bash
# First run - root creates volume
$ podman run -v myvolume:/data alpine touch /data/file
# Volume is now owned by root

# Second run - different user can't write
$ podman run -u 1000 -v myvolume:/data alpine touch /data/newfile
touch: /data/newfile: Permission denied
```

### 2. Build-time vs Runtime Permissions

```dockerfile
# This sets permissions in image, not volume!
RUN mkdir /data && chmod 777 /data

# Volume mount overlays this, using volume's permissions
```

### 3. Rootless Confusion

```bash
# Looks like root in container
$ podman exec mycontainer id
uid=0(root)

# But maps to non-root on host
$ ps aux | grep myprocess
100000  # Actual UID on host
```

## 💡 Quick Reference

### Permission Cheat Sheet

| Need | Permission | Numeric | Command |
|------|------------|---------|---------|
| Everyone read file | -r--r--r-- | 444 | `chmod 444 file` |
| Owner write, others read | -rw-r--r-- | 644 | `chmod 644 file` |
| Group shared write | -rw-rw-r-- | 664 | `chmod 664 file` |
| Directory everyone access | drwxr-xr-x | 755 | `chmod 755 dir` |
| Directory group write | drwxrwxr-x | 775 | `chmod 775 dir` |
| Sensitive group read | -rw-r----- | 640 | `chmod 640 file` |

### User/Group Management

```bash
# Add user to group
usermod -a -G groupname username

# Create group with specific GID
groupadd -g 1000 podserve

# Change file group
chgrp groupname file

# Recursive ownership change
chown -R user:group directory/
```

## 🔗 Related Documentation

- [PODMAN-BEST-PRACTICES.md](PODMAN-BEST-PRACTICES.md) - General Podman patterns
- [DEBUGGING-GUIDE.md](DEBUGGING-GUIDE.md) - Debugging permission issues
- [ARCHITECTURE-DECISIONS.md](ARCHITECTURE-DECISIONS.md) - Why we chose certain permission models

Remember: Permission issues are solvable! The key is understanding which user runs each service and planning accordingly.