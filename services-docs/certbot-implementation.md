# Certbot Service Implementation Plan

## Overview

Implement certificate management service in Python, supporting multiple certificate methods including Let's Encrypt, DNS challenges, and self-signed certificates.

## Python Implementation

### Service Class (services/certbot.py)

```python
class CertbotService(BaseService):
    def __init__(self):
        super().__init__("certbot")
        self.cert_dir = "/data/state/certificates"
        self.config_dir = "/data/config/certbot"
        
    def run_mode(self, mode):
        modes = {
            "init": self.init_certificates,
            "renew": self.renew_certificates,
            "cron": self.run_cron_mode,
            "check": self.check_certificates
        }
        return modes[mode]()
        
    def init_certificates(self):
        method = self.config.get("method", "self-signed")
        
        if method == "self-signed":
            self.create_self_signed()
        elif method == "standalone":
            self.certbot_standalone()
        elif method.startswith("dns-"):
            self.certbot_dns(method)
            
    def create_self_signed(self):
        # Generate self-signed certificates using cryptography library
        
    def certbot_standalone(self):
        # Run certbot in standalone mode
        
    def certbot_dns(self, provider):
        # Run certbot with DNS challenge
        
    def setup_cron(self):
        # Configure cron job for renewal
        
    def check_certificates(self):
        # Check certificate validity and expiration
```

### Certificate Generation

#### 1. Self-Signed Certificates

```python
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa

def create_self_signed(self):
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Generate certificate
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, self.domain),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        subject
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(self.domain),
            x509.DNSName(f"*.{self.domain}"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Save files
    self.save_certificate_files(cert, private_key)
```

#### 2. Let's Encrypt Integration

```python
def certbot_standalone(self):
    cmd = [
        "certbot", "certonly",
        "--standalone",
        "--non-interactive",
        "--agree-tos",
        "--email", self.email,
        "--domains", self.domain,
        "--cert-path", f"{self.cert_dir}/{self.domain}"
    ]
    
    if self.staging:
        cmd.append("--staging")
        
    subprocess.run(cmd, check=True)
```

#### 3. DNS Challenge Support

```python
def certbot_dns(self, provider):
    # Load provider credentials
    creds_file = f"{self.config_dir}/{provider.replace('dns-', '')}.ini"
    
    cmd = [
        "certbot", "certonly",
        f"--{provider}",
        f"--{provider}-credentials", creds_file,
        "--non-interactive",
        "--agree-tos",
        "--email", self.email,
        "--domains", self.domain
    ]
    
    subprocess.run(cmd, check=True)
```

### Renewal Management

```python
def renew_certificates(self):
    # Check each certificate
    for domain in self.get_managed_domains():
        cert_path = f"{self.cert_dir}/{domain}/fullchain.pem"
        
        if self.needs_renewal(cert_path):
            self.logger.info(f"Renewing certificate for {domain}")
            self.init_certificates()  # Re-run init for domain
            
def needs_renewal(self, cert_path, days=30):
    if not os.path.exists(cert_path):
        return True
        
    cert = x509.load_pem_x509_certificate(
        open(cert_path, 'rb').read()
    )
    
    expires = cert.not_valid_after
    days_left = (expires - datetime.utcnow()).days
    
    return days_left < days
```

### Cron Mode

```python
def run_cron_mode(self):
    # Initial certificate check
    self.init_certificates()
    
    # Setup cron job
    schedule.every().day.at("02:00").do(self.renew_certificates)
    
    # Run scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)
```

## Configuration Management

```yaml
# /data/config/certbot/config.yaml
certbot:
  domain: local.dev
  email: admin@local.dev
  staging: false
  method: self-signed  # or standalone, dns-cloudflare, etc.
  
# For DNS providers, additional files needed:
# /data/config/certbot/cloudflare.ini
# dns_cloudflare_email = email@example.com
# dns_cloudflare_api_key = your-api-key
```

## Implementation Steps

1. Create CertbotService class with mode selection
2. Implement self-signed certificate generation using cryptography
3. Add certbot command wrappers for different methods
4. Implement certificate checking and renewal logic
5. Add cron mode with scheduling
6. Create configuration management
7. Add health check for certificate validity

## Dockerfile Changes

```dockerfile
FROM localhost/podserve-base:latest

# Install certbot and plugins (as before)
...

# Additional Python dependencies
RUN pip3 install --break-system-packages \
    cryptography \
    schedule

# Run Python service
CMD ["python3", "-m", "podserve.services.certbot", "cron"]
```