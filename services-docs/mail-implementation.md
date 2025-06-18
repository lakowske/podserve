# Mail Service Implementation Plan

## Overview

Implement a mail service in Python that manages Postfix (SMTP) and Dovecot (IMAP/POP3) with virtual users, SSL/TLS support, and proper certificate handling.

## Python Implementation

### Service Class (services/mail.py)

```python
class MailService(BaseService):
    def __init__(self):
        super().__init__("mail")
        self.postfix_dir = "/etc/postfix"
        self.dovecot_dir = "/etc/dovecot"
        self.vmail_dir = "/var/mail/vhosts"
        self.vmail_uid = 5000
        self.vmail_gid = 5000
        
    def configure(self):
        # Setup SSL certificates
        # Configure Postfix
        # Configure Dovecot
        # Create virtual users
        
    def start(self):
        # Configure services
        # Start supervisor to manage both services
```

### SSL Certificate Management

```python
def setup_ssl_certificates(self):
    """Copy and set proper permissions for mail services"""
    source_cert_dir = f"/data/state/certificates/{self.mail_domain}"
    dest_cert_dir = "/etc/ssl/certs/mail"
    
    # Create destination directory
    os.makedirs(dest_cert_dir, exist_ok=True)
    
    # Copy certificates
    for cert_file in ["cert.pem", "privkey.pem", "fullchain.pem"]:
        src = os.path.join(source_cert_dir, cert_file)
        dst = os.path.join(dest_cert_dir, cert_file)
        
        if os.path.exists(src):
            shutil.copy2(src, dst)
            
            # Set permissions for Dovecot
            if cert_file == "privkey.pem":
                os.chown(dst, 0, grp.getgrnam("dovecot").gr_gid)
                os.chmod(dst, 0o640)
            else:
                os.chmod(dst, 0o644)
                
    return os.path.exists(os.path.join(dest_cert_dir, "fullchain.pem"))
```

### Postfix Configuration

```python
def configure_postfix(self):
    """Generate Postfix configuration"""
    main_cf_template = """
# Basic configuration
myhostname = {{ mail_server_name }}
mydomain = {{ mail_domain }}
myorigin = $mydomain
mydestination = localhost
mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128

# Virtual mailbox configuration
virtual_mailbox_domains = {{ mail_domain }}
virtual_mailbox_base = /var/mail/vhosts
virtual_mailbox_maps = hash:/etc/postfix/vmailbox
virtual_minimum_uid = 100
virtual_uid_maps = static:{{ vmail_uid }}
virtual_gid_maps = static:{{ vmail_gid }}
virtual_alias_maps = hash:/etc/postfix/virtual

# SMTP configuration
smtpd_banner = $myhostname ESMTP
smtpd_recipient_restrictions = 
    permit_mynetworks,
    permit_sasl_authenticated,
    reject_unauth_destination

# SASL authentication
smtpd_sasl_auth_enable = yes
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_security_options = noanonymous
smtpd_sasl_local_domain = $mydomain

{% if ssl_enabled %}
# TLS configuration
smtpd_tls_cert_file = {{ ssl_cert_file }}
smtpd_tls_key_file = {{ ssl_key_file }}
smtpd_tls_CAfile = {{ ssl_chain_file }}
smtpd_use_tls = yes
smtpd_tls_security_level = may
smtp_tls_security_level = may
{% endif %}
"""
    
    template = Template(main_cf_template)
    config = template.render(
        mail_server_name=self.mail_server_name,
        mail_domain=self.mail_domain,
        vmail_uid=self.vmail_uid,
        vmail_gid=self.vmail_gid,
        ssl_enabled=self.ssl_enabled,
        ssl_cert_file=f"/etc/ssl/certs/mail/cert.pem",
        ssl_key_file=f"/etc/ssl/certs/mail/privkey.pem",
        ssl_chain_file=f"/etc/ssl/certs/mail/fullchain.pem"
    )
    
    with open(f"{self.postfix_dir}/main.cf", "w") as f:
        f.write(config)
```

### Dovecot Configuration

```python
def configure_dovecot(self):
    """Generate Dovecot configuration"""
    dovecot_conf = """
protocols = imap pop3 lmtp

# Authentication
auth_mechanisms = plain login
passdb {
    driver = passwd-file
    args = /etc/dovecot/users
}
userdb {
    driver = static
    args = uid={{ vmail_uid }} gid={{ vmail_gid }} home=/var/mail/vhosts/%d/%n
}

# Mail location
mail_location = maildir:~/Maildir

# Service configuration
service auth {
    unix_listener /var/spool/postfix/private/auth {
        mode = 0666
        user = postfix
        group = postfix
    }
}

service lmtp {
    unix_listener /var/spool/postfix/private/dovecot-lmtp {
        mode = 0600
        user = postfix
        group = postfix
    }
}

# Logging
log_path = /dev/stderr
info_log_path = /dev/stdout
"""
    
    # Write main config
    with open(f"{self.dovecot_dir}/dovecot.conf", "w") as f:
        f.write(dovecot_conf)
    
    # SSL configuration
    if self.ssl_enabled:
        ssl_conf = """
ssl = yes
ssl_cert = <{{ ssl_cert_file }}
ssl_key = <{{ ssl_key_file }}
ssl_ca = <{{ ssl_chain_file }}
ssl_dh = </etc/dovecot/dh.pem

# SSL protocols and ciphers
ssl_min_protocol = TLSv1.2
ssl_cipher_list = HIGH:!aNULL:!MD5
ssl_prefer_server_ciphers = yes
"""
        template = Template(ssl_conf)
        config = template.render(
            ssl_cert_file="/etc/ssl/certs/mail/cert.pem",
            ssl_key_file="/etc/ssl/certs/mail/privkey.pem",
            ssl_chain_file="/etc/ssl/certs/mail/fullchain.pem"
        )
        
        with open(f"{self.dovecot_dir}/conf.d/10-ssl.conf", "w") as f:
            f.write(config)
```

### Virtual User Management

```python
class VirtualUserManager:
    def __init__(self, mail_domain, vmail_dir):
        self.mail_domain = mail_domain
        self.vmail_dir = vmail_dir
        self.users_file = "/etc/dovecot/users"
        
    def create_user(self, username, password):
        """Create a virtual mail user"""
        # Generate password hash
        password_hash = self.generate_password_hash(password)
        
        # Create maildir
        user_mail_dir = f"{self.vmail_dir}/{self.mail_domain}/{username}/Maildir"
        os.makedirs(user_mail_dir, exist_ok=True)
        os.chown(user_mail_dir, self.vmail_uid, self.vmail_gid)
        
        # Add to users file
        user_entry = f"{username}@{self.mail_domain}:{password_hash}\n"
        with open(self.users_file, "a") as f:
            f.write(user_entry)
            
        # Add to Postfix virtual mailbox
        self.update_postfix_maps(username)
        
    def generate_password_hash(self, password):
        """Generate SHA512-CRYPT password hash"""
        import crypt
        return crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
        
    def update_postfix_maps(self, username):
        """Update Postfix virtual mailbox and alias maps"""
        email = f"{username}@{self.mail_domain}"
        
        # Update vmailbox
        vmailbox_entry = f"{email}    {self.mail_domain}/{username}/Maildir/\n"
        with open("/etc/postfix/vmailbox", "a") as f:
            f.write(vmailbox_entry)
        subprocess.run(["postmap", "/etc/postfix/vmailbox"])
        
        # Update virtual aliases
        virtual_entry = f"{email}    {email}\n"
        with open("/etc/postfix/virtual", "a") as f:
            f.write(virtual_entry)
        subprocess.run(["postmap", "/etc/postfix/virtual"])
```

### Service Management with Supervisor

```python
def generate_supervisor_config(self):
    """Generate supervisor configuration for running both services"""
    supervisor_conf = """
[supervisord]
nodaemon=true
logfile=/dev/stdout
logfile_maxbytes=0
loglevel=info

[program:postfix]
command=/usr/sbin/postfix start-fg
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:dovecot]
command=/usr/sbin/dovecot -F
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
"""
    
    with open("/etc/supervisor/conf.d/mail.conf", "w") as f:
        f.write(supervisor_conf)
```

### Health Check

```python
def health_check(self):
    """Check if mail services are running"""
    checks = {
        "smtp": self.check_smtp(),
        "imap": self.check_imap(),
        "pop3": self.check_pop3()
    }
    
    all_healthy = all(check["status"] == "healthy" for check in checks.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "services": checks
    }
    
def check_smtp(self):
    """Check SMTP service on port 25"""
    try:
        with socket.create_connection(("localhost", 25), timeout=5) as sock:
            sock.sendall(b"QUIT\r\n")
            return {"status": "healthy", "port": 25}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Implementation Steps

1. Create MailService class extending BaseService
2. Implement SSL certificate copying with proper permissions
3. Create Postfix configuration generator
4. Create Dovecot configuration generator
5. Implement virtual user management system
6. Add supervisor configuration for process management
7. Implement health checks for all mail protocols
8. Add DH parameter generation for Dovecot

## Environment Variables

- `MAIL_SERVER_NAME`: Full hostname of mail server
- `MAIL_DOMAIN`: Domain for email addresses
- `SSL_CERT_FILE`, `SSL_KEY_FILE`, `SSL_CHAIN_FILE`: Certificate paths

## Directory Structure

```
/var/mail/vhosts/
└── domain.com/
    └── username/
        └── Maildir/
            ├── new/
            ├── cur/
            └── tmp/

/etc/
├── postfix/
│   ├── main.cf
│   ├── master.cf
│   ├── vmailbox
│   └── virtual
└── dovecot/
    ├── dovecot.conf
    ├── users
    └── conf.d/
        └── 10-ssl.conf
```

## Dockerfile Changes

```dockerfile
FROM localhost/podserve-base:latest

# Install mail packages (as before)
...

# Additional Python dependencies
RUN pip3 install --break-system-packages supervisor

# Run Python service
CMD ["python3", "-m", "podserve.services.mail"]
```

## Testing

```python
def test_mail_service():
    # Test SMTP
    import smtplib
    server = smtplib.SMTP('localhost', 25)
    server.quit()
    
    # Test IMAP
    import imaplib
    imap = imaplib.IMAP4('localhost')
    imap.logout()
```