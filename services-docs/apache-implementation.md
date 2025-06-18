# Apache Service Implementation Plan

## Overview

Implement Apache web server management in Python, handling SSL configuration, virtual hosts, WebDAV, and Gitweb features.

## Python Implementation

### Service Class (services/apache.py)

```python
class ApacheService(BaseService):
    def __init__(self):
        super().__init__("apache")
        self.apache_bin = "/usr/sbin/apache2"
        self.config_dir = "/etc/apache2"
        
    def configure(self):
        # Configure based on environment variables
        # Generate virtual host configs from templates
        # Enable/disable modules based on features
        
    def setup_ssl(self):
        # Auto-detect certificates
        # Configure SSL virtual host
        # Enable SSL modules
        
    def setup_webdav(self):
        # Create WebDAV directories
        # Generate digest auth file
        # Configure WebDAV virtual host
        
    def setup_gitweb(self):
        # Create git repository directories
        # Configure gitweb
        # Create sample repositories
        
    def start(self):
        # Source Apache envvars
        # Create runtime directories
        # Start Apache in foreground
```

### Configuration Templates

Create Jinja2 templates for:
- `templates/apache/000-default.conf.j2`
- `templates/apache/ssl-vhost.conf.j2`
- `templates/apache/webdav.conf.j2`
- `templates/apache/gitweb.conf.j2`

### Key Methods

#### 1. SSL Auto-Detection

```python
def detect_ssl_certificates(self):
    cert_path = f"/data/state/certificates/{self.server_name}"
    return all(os.path.exists(f"{cert_path}/{f}") 
               for f in ["cert.pem", "privkey.pem", "fullchain.pem"])
```

#### 2. Module Management

```python
def enable_modules(self, modules):
    for module in modules:
        subprocess.run(["a2enmod", module], check=True)
```

#### 3. WebDAV User Management

```python
def create_webdav_user(self, username, password):
    realm = "webdav"
    hash_input = f"{username}:{realm}:{password}"
    password_hash = hashlib.md5(hash_input.encode()).hexdigest()
    # Write to digest file
```

#### 4. Process Management

```python
def start(self):
    # Source environment variables
    env = self.load_apache_envvars()
    
    # Create required directories
    self.create_runtime_directories()
    
    # Start Apache
    os.execvpe(self.apache_bin, 
               [self.apache_bin, "-D", "FOREGROUND"],
               env)
```

## Implementation Steps

1. Create ApacheService class extending BaseService
2. Implement configuration methods for each feature
3. Create Jinja2 templates for all config files
4. Implement SSL auto-detection logic
5. Add WebDAV user management
6. Implement Git repository initialization
7. Handle Apache process lifecycle with proper signal handling

## Environment Variable Mapping

- `APACHE_SERVER_NAME` → `self.server_name`
- `SSL_ENABLED` → `self.ssl_mode`
- `WEBDAV_ENABLED` → `self.enable_webdav`
- `GITWEB_ENABLED` → `self.enable_gitweb`

## Directory Structure

```
/data/
├── state/
│   └── certificates/     # SSL certificates
├── web/
│   ├── html/            # Document root
│   ├── webdav/          # WebDAV storage
│   └── git/
│       └── repositories/ # Git repos
```

## Dockerfile Changes

```dockerfile
FROM localhost/podserve-base:latest

# Install Apache (as before)
...

# Run Python service
CMD ["python3", "-m", "podserve.services.apache"]
```