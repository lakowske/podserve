# PodServe Architecture

## Overview

PodServe is an integrated server pod that provides web, mail, and DNS services in a single Podman pod. The system is designed to run as a cohesive unit with shared networking, storage, and certificate management.

## System Components

### Core Services

1. **Web Server (Apache)**
   - Apache 2 with SSL, WebDAV, and GitWeb support
   - Serves on ports 80 (HTTP) and 443 (HTTPS)
   - Provides web hosting, WebDAV file sharing, and Git repository browsing
   - Container image: `localhost/podserve-apache:latest`

2. **Mail Server (Postfix + Dovecot)**
   - Postfix for SMTP (ports 25, 587)
   - Dovecot for IMAP (ports 143, 993)
   - Dovecot for POP3 (port 995)
   - Virtual mailbox support
   - Container image: `localhost/podserve-mail:latest`

3. **DNS Server (BIND 9)**
   - Recursive DNS with forwarding to public resolvers (8.8.8.8, 8.8.4.4)
   - DNSSEC disabled by default
   - Serves on port 53 (TCP/UDP)
   - Container image: `localhost/podserve-dns:latest`

## Pod Architecture

```
┌─────────────────────────── Podman Pod: podserve-simple ─────────────────────────┐
│                                                                                   │
│  Hostname: lab.sethlakowske.com                                                  │
│                                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                          │
│  │ Apache       │  │ Mail         │  │ DNS          │                          │
│  │ Container    │  │ Container    │  │ Container    │                          │
│  │              │  │              │  │              │                          │
│  │ - HTTP/HTTPS │  │ - SMTP       │  │ - BIND 9     │                          │
│  │ - WebDAV     │  │ - IMAP/IMAPS │  │ - Forwarding │                          │
│  │ - GitWeb     │  │ - POP3S      │  │ - No DNSSEC  │                          │
│  │ - Auto SSL   │  │ - Submission │  │              │                          │
│  └──────────────┘  └──────────────┘  └──────────────┘                          │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────┐                       │
│  │ Persistent Volume Claims                             │                       │
│  │                                                     │                       │
│  │ podserve-simple-web (10Gi)                         │                       │
│  │ - Web content and WebDAV storage                   │                       │
│  │ - Git repositories                                 │                       │
│  │                                                     │                       │
│  │ podserve-simple-mail (5Gi)                        │                       │
│  │ - Virtual mailbox storage                          │                       │
│  │ - Mail queue data                                  │                       │
│  │                                                     │                       │
│  │ podserve-certificates (shared)                     │                       │
│  │ - SSL/TLS certificates                             │                       │
│  │ - Certificate management                           │                       │
│  └─────────────────────────────────────────────────────┘                       │
│                                                                                   │
│  Port Mappings:                                                                  │
│  - 53:53/tcp,udp (DNS)                                                          │
│  - 80:80/tcp (HTTP)                                                             │
│  - 443:443/tcp (HTTPS)                                                          │
│  - 25:25/tcp (SMTP)                                                             │
│  - 587:587/tcp (Submission)                                                     │
│  - 143:143/tcp (IMAP)                                                           │
│  - 993:993/tcp (IMAPS)                                                          │
│  - 995:995/tcp (POP3S)                                                          │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Volume Architecture

### Persistent Volume Claims

1. **podserve-certificates** (`/data/state/certificates`)
   - SSL/TLS certificates for all services
   - Shared read-only across Apache and Mail containers
   - Certificate management and renewal

2. **podserve-simple-web** (`/data/web`)
   - 10Gi storage capacity
   - Web document root and content
   - WebDAV storage
   - Git repositories
   - Mounted to Apache container

3. **podserve-simple-mail** (`/var/mail/vhosts`)
   - 5Gi storage capacity
   - Virtual mailbox storage
   - Mail queue data
   - User mail directories
   - Mounted to Mail container

## Network Architecture

### Pod Network
- All containers share the same network namespace
- Inter-container communication via localhost
- Pod hostname: lab.sethlakowske.com

### DNS Resolution
- DNS container provides recursive DNS resolution
- Forwards queries to public resolvers (8.8.8.8, 8.8.4.4)
- DNSSEC validation disabled

### Service Discovery
- Apache: lab.sethlakowske.com (primary hostname)
- Mail: mail.lab.sethlakowske.com
- Host aliases configured for localhost resolution

## Security Architecture

### Certificate Management
- Certificates stored in shared persistent volume
- Shared read-only across Apache and Mail containers
- Automatic SSL certificate generation and management
- TLS/SSL encryption for HTTPS and mail services

### Network Security
- Pod network isolation within Kubernetes namespace
- Direct port mapping to host for external access
- TLS/SSL encryption for public-facing services
- Internal communication via shared pod network

## Container Dependencies

### Startup Order
- All containers start in parallel (no init container)
- DNS container provides resolution for other services
- Apache and Mail containers can start independently

### Runtime Dependencies
- Apache and Mail depend on certificate volume for TLS
- All containers share the same pod network
- Health checks ensure service availability

## Data Persistence

### Persistent Volumes
- Three persistent volume claims provide data persistence
- Volume data persists across pod restarts and recreations
- ReadWriteOnce access mode for all volumes

### State Management
- Web content stored in podserve-simple-web (10Gi)
- Mail data stored in podserve-simple-mail (5Gi)
- Certificates stored in shared podserve-certificates volume

## Health Monitoring

### Container Health Checks

1. **Apache Container**
   - Liveness probe: HTTP GET to localhost/
   - Readiness probe: HTTP GET to localhost/
   - Probe intervals: 3 seconds
   - Failure thresholds: 5 attempts

2. **Mail Container**
   - Liveness probe: SMTP connection test to port 25
   - Readiness probe: SMTP connection test to port 25
   - Probe intervals: 3 seconds
   - Failure thresholds: 5 attempts

3. **DNS Container**
   - Liveness probe: DNS query for google.com
   - Readiness probe: DNS query for google.com
   - Probe intervals: 3 seconds
   - Failure thresholds: 5 attempts

### Pod Resilience
- Restart policy: Always
- Automatic recovery from container failures
- Health checks ensure service availability before traffic routing

## Container Images

All containers are built from the local docker directory:

### Base Images
- **podserve-base**: Common base image with health check utilities
- **podserve-apache**: Apache web server with SSL, WebDAV, and GitWeb
- **podserve-mail**: Postfix/Dovecot mail server with SSL support
- **podserve-dns**: BIND 9 DNS server with forwarding configuration

### Build Process
- Images built using `docker/build.sh` script
- Local registry: `localhost/podserve-*:latest`
- Container configuration in respective docker subdirectories