# Claude Development Notes

This file contains important lessons and reminders for future development sessions.

> **📚 Note**: This documentation has been reorganized! 
> - For the main entry point, see [QUICKSTART.md](QUICKSTART.md)
> - For core principles, see [docs/PRINCIPLES.md](docs/PRINCIPLES.md)
> - For debugging help, see [docs/DEBUGGING-GUIDE.md](docs/DEBUGGING-GUIDE.md)
> - For auto-loaded context, see [.claude/context.md](.claude/context.md)

## Server Configuration Troubleshooting

### Always Consult Official Documentation First

**Lesson Learned:** When encountering server configuration errors, always consult the official server documentation BEFORE attempting complex troubleshooting.

**Example Case - Dovecot SSL Configuration:**
- **Problem:** Dovecot SSL context initialization failing with "Can't load SSL certificate: There is no valid PEM certificate"
- **Time Spent:** Hours troubleshooting permissions, certificate formats, SSL ciphers, file copying approaches
- **Root Cause:** Incorrect Dovecot configuration syntax - missing `<` prefix for file paths
- **Solution:** `ssl_cert = <${SSL_CERT_FILE}` instead of `ssl_cert = ${SSL_CERT_FILE}`

**Key Insight:** The `<` prefix in Dovecot config tells it to read from file vs. expecting inline content - this is basic Dovecot syntax that would have been found immediately in documentation.

### Documentation-First Approach

When encountering server configuration issues:

1. **Read the official documentation** for the specific server/service
2. **Check configuration syntax** - many servers have specific syntax requirements  
3. **Look for working examples** in documentation or reference configurations
4. **Validate configuration** using server-specific tools (e.g., `doveconf`, `nginx -t`, `apache2ctl configtest`)
5. Only then proceed to advanced troubleshooting (permissions, certificates, etc.)

### Reference Configurations

The project contains working reference configurations in `/reference-docker/` - always check these when current configs aren't working. In this case, `/reference-docker/mail/config/dovecot-ssl.conf` contained the correct syntax with `<` prefixes.

## Container Logging Best Practices

- **Always use stdout/stderr** for container logs (not files)
- **Configure services** to log to stdout/stderr using service-specific methods
- **Remove log volumes** from container configurations when implementing proper container logging
- **Test with `podman logs`** to verify logging is working correctly

## Volume Mount Permissions - CRITICAL LESSON

**ALWAYS use `--userns=keep-id` with volume mounts for developer-friendly containers**

```bash
# ❌ THIS FAILS - Permission denied on volume writes
podman run -v ./data:/data/state service-image

# ✅ THIS WORKS - Preserves user namespace mapping
podman run --userns=keep-id -v ./data:/data/state:Z service-image
```

**Why**: Podman's default user namespace mapping causes mounted directories to appear as `root:root` inside containers, even when owned by the developer on the host. This blocks all volume write operations.

**Solution applies to**: ALL services requiring persistent storage. See PERMISSIONS-GUIDE.md for complete implementation patterns.

## DNS Service Configuration - BIND9 Syntax

**Lesson Learned:** BIND9 has specific configuration syntax that differs from other servers - always verify against official BIND9 documentation.

**Example Case - DNS Service Implementation:**
- **Problem:** BIND9 failing to start with "undefined ACL 'yes'" and duplicate zone definitions
- **Root Causes:** 
  1. Incorrect recursion syntax: `allow-recursion { yes; }` instead of `recursion yes;`
  2. Duplicate localhost zones when domain defaults to "localhost"
- **Solutions:**
  1. Use `recursion yes;` (boolean directive) not `allow-recursion { yes; }` (ACL syntax)
  2. Conditionally include built-in zones to avoid conflicts with custom domains

**Key Insight:** BIND9 has specific syntax for boolean directives vs. ACL directives - this is fundamental BIND9 syntax covered in basic documentation.

**Implementation Pattern:**
```python
# ✅ Correct BIND9 syntax
f"recursion {self.allow_recursion};"  # Boolean directive

# ❌ Incorrect - ACL syntax for boolean
f"allow-recursion {{ {self.allow_recursion}; }};"  # Treats 'yes' as ACL name

# ✅ Conditional zone inclusion to avoid conflicts  
{'' if self.domain == 'localhost' else 'zone "localhost" { ... };'}
```

## Container Development Best Practices

### Base Image Updates
When modifying service source code, **always rebuild the base image first** before rebuilding specific services:

```bash
# ✅ Correct sequence for python-harmony changes
./build-dev.sh base     # Updates source code in base image
./build-dev.sh dns      # Builds service with updated base
```

**Why**: Service containers inherit from base images that contain the Python source code. Changes to `src/` files require base image rebuild to take effect.

## Build Commands

For this project:
- **Build mail container:** `cd docker && ./build.sh mail`  
- **Deploy pod:** `podman play kube simple.yaml`
- **Check logs:** `podman logs podserve-simple-mail`
- **Run tests:** `venv/bin/pytest tests/test_mail_integration.py -v`

For python-harmony implementation:
- **Build base:** `cd implementations/python-harmony/docker && ./build-dev.sh base`
- **Build specific service:** `./build-dev.sh <service-name>`
- **Test isolation:** `podman run --rm --userns=keep-id -e LOG_LEVEL=DEBUG localhost/podserve-harmony-<service>:latest`