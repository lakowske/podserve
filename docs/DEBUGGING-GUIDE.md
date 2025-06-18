# PodServe Debugging Guide

This guide helps you quickly diagnose and fix common issues in PodServe development.

## 🚦 Quick Diagnostics Checklist

When something isn't working, check these in order:

1. **Return Values** ⚠️
   - Check all `run_subprocess()` calls return `True` not `None`
   - Verify boolean return patterns in service methods
   
2. **Logging Level**
   - Set `LOG_LEVEL=DEBUG` environment variable
   - Check logs are actually appearing
   
3. **Template Rendering**
   - Verify templates exist at expected paths
   - Check template variables are defined
   - Test template rendering in isolation
   
4. **Process Execution**
   - Test commands manually in container
   - Check file permissions and ownership
   - Verify required binaries are installed

## 🔴 Common Issues and Solutions

### Issue: "Service configuration failed" with no specific error

**Symptoms:**
- Service exits immediately
- Generic error message
- No detailed error output

**Diagnosis Steps:**
```bash
# 1. Enable debug logging
podman run --rm -e LOG_LEVEL=DEBUG localhost/podserve-mail:latest mail

# 2. Check for None return values
grep -n "return None" src/podserve/core/service.py
grep -n "return$" src/podserve/core/service.py  # Empty returns

# 3. Add debug prints in service methods
```

**Common Causes:**
1. **Return value issue** (90% of cases):
```python
# Wrong - returns None
def run_subprocess(self, command):
    result = subprocess.run(command)
    if result.returncode != 0:
        return False
    # Missing return True!

# Correct
def run_subprocess(self, command):
    result = subprocess.run(command)
    if result.returncode != 0:
        return False
    return True  # Explicit return
```

2. **Exception swallowing**:
```python
# Wrong - hides real error
try:
    self.configure()
except Exception:
    return False  # Lost exception details

# Correct
try:
    self.configure()
except Exception as e:
    self.logger.error(f"Configuration failed: {str(e)}")
    raise  # Or return False with context
```

### Issue: SSL/TLS Certificate Errors

**Symptoms:**
- "Can't load SSL certificate"
- "No valid PEM certificate" 
- SSL handshake failures

**Common Causes:**

1. **Dovecot configuration syntax**:
```bash
# Wrong - missing < prefix
ssl_cert = /data/state/certificates/cert.pem

# Correct - < tells Dovecot to read file
ssl_cert = </data/state/certificates/cert.pem
```

2. **File permissions**:
```bash
# Check certificate permissions
podman exec podserve-simple-mail ls -la /data/state/certificates/

# Fix permissions if needed
podman exec podserve-simple-mail chmod 644 /data/state/certificates/cert.pem
podman exec podserve-simple-mail chmod 600 /data/state/certificates/key.pem
```

3. **Certificate format issues**:
```bash
# Verify certificate format
podman exec podserve-simple-mail openssl x509 -in /data/state/certificates/cert.pem -text -noout

# Check key format
podman exec podserve-simple-mail openssl rsa -in /data/state/certificates/key.pem -check
```

### Issue: Template Rendering Failures

**Symptoms:**
- Configuration files empty or missing
- Jinja2 undefined variable errors
- Services can't find config files

**Diagnosis:**
```python
# Add debug logging to template rendering
self.logger.debug(f"Rendering template: {template_name}")
self.logger.debug(f"Template context: {context}")
self.logger.debug(f"Output path: {output_path}")
```

**Common Fixes:**

1. **Check template paths**:
```python
# Use absolute paths or proper resolution
template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'mail')
```

2. **Verify template variables**:
```python
# Define all required variables
context = {
    'domain': os.environ.get('DOMAIN', 'example.com'),
    'ssl_cert': os.environ.get('SSL_CERT_FILE', '/data/state/certificates/cert.pem'),
    # Don't forget any variable used in template!
}
```

3. **Test template rendering**:
```python
# Standalone test
from jinja2 import Template
with open('template.j2') as f:
    template = Template(f.read())
print(template.render(context))
```

### Issue: Container Won't Start

**Symptoms:**
- Container exits immediately
- No logs produced
- Health checks never pass

**Diagnosis Steps:**

1. **Run interactively**:
```bash
# Override entrypoint to get shell
podman run -it --rm --entrypoint /bin/bash localhost/podserve-mail:latest

# Try to run service manually
python3 -m podserve.services.mail
```

2. **Check dependencies**:
```bash
# Verify Python packages
python3 -c "import podserve.core.service"

# Check system packages
which postfix dovecot
```

3. **Examine startup sequence**:
```python
# Add logging to __init__ methods
def __init__(self, debug=False):
    self.logger.info("Initializing mail service")
    super().__init__('mail', debug)
    self.logger.info("Mail service initialized")
```

### Issue: Service Commands Fail

**Symptoms:**
- Subprocess commands return non-zero
- "Command not found" errors
- Permission denied errors

**Diagnosis:**

1. **Test commands manually**:
```bash
# Enter container
podman exec -it podserve-simple-mail bash

# Run exact command
postfix check
dovecot -n
```

2. **Check command construction**:
```python
# Log exact command being run
self.logger.info(f"Running command: {' '.join(command)}")
self.logger.info(f"Working directory: {os.getcwd()}")
self.logger.info(f"Environment: {os.environ}")
```

3. **Common command issues**:
```python
# Wrong - missing quotes for spaces
command = ['cp', source_file, '/path with spaces/dest']

# Correct - proper handling
command = ['cp', source_file, '/path with spaces/dest']  # subprocess handles it
```

### Issue: Inter-Service Communication Fails

**Symptoms:**
- Can't connect to other services
- "Connection refused" errors
- DNS resolution failures

**Solutions:**

1. **Use localhost in pods**:
```python
# Correct - containers share network
smtp = smtplib.SMTP('localhost', 25)

# Wrong - no container DNS names
smtp = smtplib.SMTP('mail', 25)
```

2. **Check service is listening**:
```bash
# Verify ports are open
podman exec podserve-simple-mail netstat -tlnp
podman exec podserve-simple-apache curl http://localhost:80
```

3. **Timing issues**:
```python
# Add retry logic for service dependencies
for attempt in range(5):
    try:
        connection = connect_to_service()
        break
    except ConnectionError:
        time.sleep(2)
```

## 🔧 Debugging Tools and Techniques

### 1. Enhanced Logging

```python
# Comprehensive logging setup
import logging
import sys

def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    
    # File handler for debugging
    file_handler = logging.FileHandler('/data/logs/service.log')
    file_handler.setLevel(logging.DEBUG)
    
    # Detailed formatter for debugging
    debug_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    console.setFormatter(debug_formatter)
    file_handler.setFormatter(debug_formatter)
    
    logger = logging.getLogger()
    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.setLevel(level)
```

### 2. Container Inspection

```bash
# Full container inspection
podman inspect podserve-simple-mail > mail-inspect.json

# Key things to check:
# - Mounts section (volumes)
# - Config.Env (environment variables)
# - NetworkSettings
# - State (exit code, status)

# Process listing
podman exec podserve-simple-mail ps aux

# File system state
podman exec podserve-simple-mail find /data -type f -name "*.conf" | head -20
```

### 3. Interactive Debugging

```python
# Add breakpoints for debugging
import pdb

def problematic_method(self):
    # ... some code ...
    pdb.set_trace()  # Drops into debugger
    # ... more code ...
```

```bash
# Run container with stdin attached
podman run -it --rm localhost/podserve-mail:latest mail
```

### 4. Health Check Debugging

```python
# Verbose health checks
def health_check(self):
    checks = {
        'process_running': self.check_process(),
        'port_open': self.check_port(),
        'config_valid': self.check_config(),
        'can_connect': self.check_connection()
    }
    
    for check, result in checks.items():
        self.logger.info(f"Health check '{check}': {'PASS' if result else 'FAIL'}")
    
    return all(checks.values())
```

## 📊 Performance Debugging

### Slow Startup
1. Add timing logs:
```python
import time

start = time.time()
self.configure()
self.logger.info(f"Configuration took {time.time() - start:.2f}s")
```

2. Profile subprocess calls:
```python
def run_subprocess(self, command):
    start = time.time()
    result = subprocess.run(command, capture_output=True)
    elapsed = time.time() - start
    if elapsed > 1.0:
        self.logger.warning(f"Slow command ({elapsed:.2f}s): {' '.join(command)}")
```

### Memory Issues
```bash
# Monitor memory usage
podman stats --no-stream

# Check for memory leaks
podman exec podserve-simple-mail cat /proc/meminfo
```

## 🚨 Emergency Procedures

### When Everything is Broken

1. **Clean slate**:
```bash
# Remove everything and start fresh
podman pod rm -f podserve-simple
podman volume prune -f
podman image prune -a -f
```

2. **Minimal test**:
```bash
# Test individual service
podman run --rm -it localhost/podserve-base:latest /bin/bash
```

3. **Compare with reference**:
```bash
# Check reference configurations
ls -la reference-docker/mail/config/
diff actual-config.conf reference-docker/mail/config/dovecot.conf
```

### Getting Help

When asking for help, provide:
1. Exact error message
2. Debug logs (`LOG_LEVEL=DEBUG`)
3. Container inspect output
4. What you've already tried

Remember: Most issues are simple once you find them. The challenge is looking in the right place!