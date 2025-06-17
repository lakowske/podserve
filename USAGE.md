# PodServe Usage Guide

PodServe is an integrated server pod providing web, mail, and DNS services in a single Podman pod. This guide covers deployment and management of the system.

For architectural details, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Prerequisites

- Podman 4.0 or higher
- At least 15GB of available storage for persistent volumes
- Network ports 53, 80, 443, 25, 587, 143, 993, 995 available
- Linux system with systemd (for auto-start functionality)

## Quick Start with Kubernetes YAML

The recommended way to deploy PodServe is using the provided Kubernetes YAML configurations.

### 1. Deploy Simple Pod Configuration

```bash
# Deploy the complete pod with all services
podman play kube simple.yaml

# Check deployment status
podman pod ps
podman ps --pod
```

The `simple.yaml` configuration includes:
- **Apache container**: Web server with SSL, WebDAV, and GitWeb
- **Mail container**: Postfix/Dovecot with SMTP, IMAP, and POP3
- **DNS container**: BIND 9 with recursive resolution
- **Persistent volumes**: 10Gi web storage, 5Gi mail storage, shared certificates

### 2. Certificate Management (Optional)

For Let's Encrypt certificates:

```bash
# Deploy certificate management pod
podman play kube certificates.yaml

# Check certificate generation
podman logs podserve-certificates-certbot
```

The `certificates.yaml` pod handles:
- Let's Encrypt certificate generation and renewal
- Standalone HTTP-01 challenge validation
- Certificate storage in shared volume

### 3. Verify Services

```bash
# Test web server
curl http://localhost/
curl -k https://localhost/

# Test DNS
dig @localhost google.com

# Test mail connectivity
telnet localhost 25
telnet localhost 143
```

## Pod Management

### Managing the Complete Pod

```bash
# Start the entire pod
podman pod start podserve-simple

# Stop the entire pod
podman pod stop podserve-simple

# Restart the entire pod
podman pod restart podserve-simple

# Remove the pod and redeploy
podman pod stop podserve-simple
podman pod rm podserve-simple
podman play kube simple.yaml

# View pod status
podman pod ps
podman ps --pod
```

### Managing Individual Services

```bash
# Restart a specific service
podman restart podserve-simple-apache
podman restart podserve-simple-mail
podman restart podserve-simple-dns

# View logs for a specific service
podman logs -f podserve-simple-apache
podman logs -f podserve-simple-mail
podman logs -f podserve-simple-dns

# Execute commands in a container
podman exec -it podserve-simple-apache bash
podman exec -it podserve-simple-mail bash
podman exec -it podserve-simple-dns bash

# Check container health status
podman ps --format "table {{.Names}}\t{{.Status}}"
```

### Environment Configuration

The pod hostname and services are configured via environment variables in `simple.yaml`:

```yaml
# Apache configuration
env:
- name: APACHE_SERVER_NAME
  value: "lab.sethlakowske.com"
- name: SSL_ENABLED
  value: "auto"
- name: WEBDAV_ENABLED
  value: "true"
- name: GITWEB_ENABLED
  value: "true"

# Mail configuration  
env:
- name: MAIL_SERVER_NAME
  value: "mail.lab.sethlakowske.com"
- name: MAIL_DOMAIN
  value: "lab.sethlakowske.com"

# DNS configuration
env:
- name: DNS_FORWARDERS
  value: "8.8.8.8;8.8.4.4"
- name: DNSSEC_ENABLED
  value: "no"
```

## Certificate Management

### Using Let's Encrypt with certificates.yaml

For production deployments with valid domain names:

```bash
# Deploy certificate management pod (requires valid domain)
podman play kube certificates.yaml

# Monitor certificate generation
podman logs -f podserve-certificates-certbot

# Certificate files are stored in shared volume
podman exec podserve-simple-apache ls -la /data/state/certificates/lab.sethlakowske.com/
```

### Manual Certificate Operations

```bash
# Check certificate status in Apache container
podman exec podserve-simple-apache openssl x509 -in /data/state/certificates/lab.sethlakowske.com/cert.pem -text -noout

# Generate self-signed certificates for testing
podman exec podserve-simple-apache openssl req -x509 -newkey rsa:4096 -keyout /data/state/certificates/lab.sethlakowske.com/privkey.pem -out /data/state/certificates/lab.sethlakowske.com/cert.pem -days 365 -nodes

# Copy certificate for chain file
podman exec podserve-simple-apache cp /data/state/certificates/lab.sethlakowske.com/cert.pem /data/state/certificates/lab.sethlakowske.com/fullchain.pem
```

### Certificate Volume Structure

Certificates are stored in the shared `podserve-certificates` volume:

```
/data/state/certificates/
└── lab.sethlakowske.com/
    ├── cert.pem       # Server certificate
    ├── privkey.pem    # Private key
    └── fullchain.pem  # Certificate chain
```

## Service Operations

### DNS Management

```bash
# Test DNS resolution
dig @localhost google.com
dig @localhost lab.sethlakowske.com

# Check DNS server status from inside container
podman exec podserve-simple-dns rndc status

# Reload DNS configuration
podman exec podserve-simple-dns rndc reload

# View DNS query logs
podman logs podserve-simple-dns | grep query
```

### Mail Server Operations

```bash
# Test SMTP connectivity
telnet localhost 25
# Expected: 220 lab.sethlakowske.com ESMTP Postfix

# Test IMAP connectivity  
telnet localhost 143
# Expected: * OK [CAPABILITY IMAP4rev1 ...] Dovecot ready

# Check mail queue
podman exec podserve-simple-mail postqueue -p

# Send test email (requires configured mailbox)
podman exec podserve-simple-mail echo "Test message" | mail -s "Test Subject" test@lab.sethlakowske.com

# View mail logs
podman logs podserve-simple-mail | grep -E "(postfix|dovecot)"

# Check mail storage
podman exec podserve-simple-mail ls -la /var/mail/vhosts/
```

### Web Server Operations

```bash
# Test HTTP/HTTPS access
curl http://localhost/
curl -k https://localhost/

# Check Apache configuration
podman exec podserve-simple-apache apache2ctl -S

# Access WebDAV (if enabled)
curl -k https://localhost/webdav/
# Default WebDAV credentials: admin / changeme

# Access GitWeb (if enabled)
curl -k https://localhost/git/

# Check virtual host configuration
podman exec podserve-simple-apache apache2ctl -D DUMP_VHOSTS

# View Apache access logs
podman logs podserve-simple-apache | grep "GET\|POST"
```

## Backup and Restore

### Backup Persistent Volumes

```bash
# Create backup directory
mkdir -p ./backups

# Stop the pod
podman pod stop podserve-simple

# Backup all persistent volumes
for vol in certificates simple-web simple-mail; do
  echo "Backing up podserve-$vol..."
  podman run --rm \
    -v podserve-$vol:/data \
    -v $(pwd)/backups:/backup \
    alpine tar czf /backup/podserve-$vol-$(date +%Y%m%d).tar.gz -C /data .
done

# Restart the pod
podman pod start podserve-simple
```

### Restore Volumes

```bash
# Stop and remove the pod
podman pod stop podserve-simple
podman pod rm podserve-simple

# Remove existing volumes (CAUTION: This deletes all data)
podman volume rm podserve-certificates podserve-simple-web podserve-simple-mail

# Recreate volumes by deploying the pod
podman play kube simple.yaml
podman pod stop podserve-simple

# Restore volumes from backup
for vol in certificates simple-web simple-mail; do
  echo "Restoring podserve-$vol..."
  podman run --rm \
    -v podserve-$vol:/data \
    -v $(pwd)/backups:/backup \
    alpine tar xzf /backup/podserve-$vol-20240315.tar.gz -C /data
done

# Start the restored pod
podman pod start podserve-simple
```

### Volume Information

The persistent volumes created by `simple.yaml`:

- **podserve-certificates**: SSL/TLS certificates (shared across Apache and Mail)
- **podserve-simple-web**: 10Gi web content, WebDAV files, Git repositories
- **podserve-simple-mail**: 5Gi mail storage, virtual mailboxes

## Systemd Integration

### Create Systemd Service

```bash
# Generate systemd files for the pod
mkdir -p ~/.config/systemd/user
cd ~/.config/systemd/user

# Generate systemd unit files from the running pod
podman generate systemd --new --files --name podserve-simple

# Enable and start the pod service
systemctl --user enable pod-podserve-simple.service
systemctl --user start pod-podserve-simple.service

# Check service status
systemctl --user status pod-podserve-simple.service
```

### Auto-start on Boot

```bash
# Enable lingering for user (allows services to start without login)
loginctl enable-linger $USER

# Verify lingering is enabled
loginctl show-user $USER | grep Linger

# Pod will now start automatically on system boot
```

### Systemd Service Management

```bash
# Start the pod
systemctl --user start pod-podserve-simple.service

# Stop the pod
systemctl --user stop pod-podserve-simple.service

# Restart the pod
systemctl --user restart pod-podserve-simple.service

# Check service logs
journalctl --user -u pod-podserve-simple.service -f

# Disable auto-start
systemctl --user disable pod-podserve-simple.service
```

## Troubleshooting

### Health Check and Status

```bash
# Check overall pod and container status
podman pod ps
podman ps --pod --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Inspect pod configuration
podman pod inspect podserve-simple

# Check resource usage
podman pod stats podserve-simple

# Test health checks manually
podman exec podserve-simple-apache curl -f http://localhost/
podman exec podserve-simple-mail bash -c "echo 'QUIT' | nc -w 1 localhost 25"
podman exec podserve-simple-dns dig @127.0.0.1 google.com A +short
```

### Common Issues

1. **Port conflicts**
   ```bash
   # Check if required ports are available
   ss -tlnp | grep -E ':(53|80|443|25|587|143|993|995)'
   
   # If conflicts exist, stop conflicting services:
   sudo systemctl stop apache2   # If Apache is running on host
   sudo systemctl stop bind9     # If BIND is running on host
   ```

2. **Container startup failures**
   ```bash
   # Check individual container logs for errors
   podman logs podserve-simple-apache
   podman logs podserve-simple-mail  
   podman logs podserve-simple-dns
   
   # Check container exit codes
   podman ps -a --filter name=podserve-simple
   ```

3. **Certificate issues**
   ```bash
   # Check if certificates exist
   podman exec podserve-simple-apache ls -la /data/state/certificates/lab.sethlakowske.com/
   
   # Verify certificate validity
   podman exec podserve-simple-apache openssl x509 -in /data/state/certificates/lab.sethlakowske.com/cert.pem -text -noout
   
   # Test SSL configuration
   podman exec podserve-simple-apache apache2ctl configtest
   ```

4. **Volume mounting issues**
   ```bash
   # Check volume status
   podman volume ls | grep podserve
   podman volume inspect podserve-certificates
   
   # Check volume permissions (if using rootless podman)
   podman unshare ls -la $(podman volume inspect podserve-certificates --format '{{.Mountpoint}}')
   ```

5. **Network connectivity issues**
   ```bash
   # Test external network from containers
   podman exec podserve-simple-dns dig @8.8.8.8 google.com
   podman exec podserve-simple-apache curl -I http://google.com
   
   # Test inter-container communication
   podman exec podserve-simple-apache nc -zv localhost 53
   podman exec podserve-simple-mail nc -zv localhost 80
   ```

### Performance Issues

```bash
# Run performance tests
make test-performance

# Check shutdown times
make benchmark-shutdown

# View performance report
make performance-report
```

### Logs and Debugging

```bash
# View all container logs
podman logs podserve-simple-apache | tail -50
podman logs podserve-simple-mail | tail -50  
podman logs podserve-simple-dns | tail -50

# Follow logs in real-time
podman logs -f podserve-simple-apache

# Search for specific errors
podman logs podserve-simple-apache | grep -i error
podman logs podserve-simple-mail | grep -i "warning\|error\|fail"

# Check system journal for podman issues
journalctl -u user@$(id -u).service | grep podman
```

## Advanced Configuration

### Customizing the Deployment

To customize the deployment, modify the `simple.yaml` file:

1. **Change hostname and domain**:
   ```yaml
   spec:
     hostname: your-domain.com
     hostAliases:
     - ip: "127.0.0.1"
       hostnames:
       - "your-domain.com"
   ```

2. **Modify environment variables**:
   ```yaml
   env:
   - name: APACHE_SERVER_NAME
     value: "your-domain.com"
   - name: MAIL_DOMAIN
     value: "your-domain.com"
   ```

3. **Adjust resource limits**:
   ```yaml
   resources:
     limits:
       memory: "1Gi"
       cpu: "500m"
     requests:
       memory: "512Mi"
       cpu: "250m"
   ```

### Performance Optimization

The system includes optimized health checks and shutdown procedures:

- **Health check intervals**: 3 seconds (aggressive monitoring)
- **Failure thresholds**: 5 attempts before marking unhealthy
- **Graceful shutdown**: Optimized for fast container shutdown (< 5 seconds)

### Using Different Container Images

To use custom or updated images, modify the `image` fields in `simple.yaml`:

```yaml
containers:
- name: apache
  image: your-registry/podserve-apache:v2.0
- name: mail  
  image: your-registry/podserve-mail:v2.0
- name: dns
  image: your-registry/podserve-dns:v2.0
```

### Development and Testing

The project includes comprehensive testing and benchmarking tools:

```bash
# Build images locally
make build

# Run integration tests
make test-integration

# Run performance benchmarks
make benchmark

# Deploy and test
make deploy
```

## Security Best Practices

### Container Security

1. **Use rootless Podman**
   ```bash
   # Verify running in rootless mode
   podman info | grep rootless
   # Should show: rootless: true
   ```

2. **Certificate Security**
   - Use Let's Encrypt certificates for production (`certificates.yaml`)
   - Certificates are shared read-only across containers
   - Regular certificate renewal via automated tools

3. **Network Security**
   - Containers share pod network namespace (internal communication)
   - Only necessary ports exposed to host
   - TLS/SSL encryption for all public services

### Volume Security

The persistent volumes use secure mounting:
- **Certificates volume**: Read-only access for service containers
- **Application volumes**: Proper ownership and permissions
- **Volume isolation**: Each application has dedicated storage

### Access Control

1. **Default credentials** (change immediately):
   - WebDAV: admin / changeme
   - Modify in Apache container configuration

2. **Firewall configuration**:
   ```bash
   # Example: Restrict access to specific networks
   sudo ufw allow from 192.168.1.0/24 to any port 443
   sudo ufw allow from 192.168.1.0/24 to any port 25
   ```

3. **Service hardening**:
   - Apache runs with minimal required modules
   - Mail server uses virtual mailboxes (no system users)
   - DNS server disables unnecessary features

### Maintenance

1. **Regular updates**:
   ```bash
   # Rebuild containers with latest base images
   make build
   
   # Redeploy with updated images
   podman pod stop podserve-simple
   podman pod rm podserve-simple
   podman play kube simple.yaml
   ```

2. **Monitor logs**:
   ```bash
   # Check for security events
   podman logs podserve-simple-apache | grep -i "error\|fail\|denied"
   podman logs podserve-simple-mail | grep -i "authentication\|reject"
   ```

3. **Backup critical data**:
   ```bash
   # Regular backups of certificates and data
   make backup  # If implemented in Makefile
   ```

### Recommended Production Settings

For production deployments:

1. **Use valid domain names** and Let's Encrypt certificates
2. **Configure firewall** to restrict access
3. **Enable log monitoring** and alerting
4. **Regular security updates** of container images
5. **Backup strategy** for persistent volumes
6. **Monitor resource usage** and set appropriate limits