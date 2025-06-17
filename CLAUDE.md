# Claude Development Notes

This file contains important lessons and reminders for future development sessions.

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

## Build Commands

For this project:
- **Build mail container:** `cd docker && ./build.sh mail`  
- **Deploy pod:** `podman play kube simple.yaml`
- **Check logs:** `podman logs podserve-simple-mail`
- **Run tests:** `venv/bin/pytest tests/test_mail_integration.py -v`