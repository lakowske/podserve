# Phase 4: Integration Planning - Certificate Service

**Service**: Certificate Service  
**Status**: Phase 2 & 3 Complete  
**Date**: 2025-06-18

## Integration Analysis

### Certificate Service Position in Architecture

```
Foundation Services (No Dependencies):
├── Certificate Service ✅ (Phases 1-3 Complete)
└── DNS Service (Next - No certificate dependency)

SSL-Dependent Services (Require Certificates):
├── Apache/Web Server (HTTPS)
├── Mail Server (SMTP/IMAP SSL)
└── Admin Interfaces (HTTPS)

Network Services (Independent):
├── DHCP Server
└── Monitoring Services
```

## Certificate Consumption Patterns

### Pattern 1: Web Services (Apache, Admin UIs)
**Dependency**: Certificates → Web Service

```yaml
# Integration Pattern: Shared Volume Mount
spec:
  containers:
  - name: certificates
    image: localhost/podserve-harmony-certificates:latest
    command: ["python3", "-m", "podserve", "certificates", "--mode", "cron"]
    volumeMounts:
    - name: ssl-certs
      mountPath: /data/state/certificates
      
  - name: apache
    image: localhost/podserve-harmony-apache:latest
    volumeMounts:
    - name: ssl-certs
      mountPath: /etc/ssl/podserve
      readOnly: true
    depends_on:
    - certificates
```

**Integration Tests Required**:
- [ ] Certificate service generates certificates
- [ ] Apache can read certificates from shared volume
- [ ] Apache SSL configuration loads certificates correctly
- [ ] HTTPS connections work with generated certificates
- [ ] Certificate renewal updates are picked up by Apache

### Pattern 2: Mail Services (Dovecot, Postfix)
**Dependency**: Certificates → Mail Service

```yaml
# Integration Pattern: Certificate Volume + Mail Config
spec:
  containers:
  - name: certificates
    # Same as above
    
  - name: mail
    image: localhost/podserve-harmony-mail:latest
    volumeMounts:
    - name: ssl-certs
      mountPath: /data/ssl
      readOnly: true
    environment:
    - SSL_CERT_FILE=/data/ssl/fullchain.pem
    - SSL_KEY_FILE=/data/ssl/privkey.pem
```

**Integration Tests Required**:
- [ ] Mail service waits for certificates to be available
- [ ] SMTP/IMAP SSL connections work
- [ ] Certificate paths correctly configured in Dovecot/Postfix
- [ ] Certificate renewal handling

### Pattern 3: Independent Foundation Services (DNS)
**Dependency**: None - Can develop in parallel

```yaml
# No certificate dependency
spec:
  containers:
  - name: dns
    image: localhost/podserve-harmony-dns:latest
    ports:
    - "53:53/udp"
    - "53:53/tcp"
```

## Shared Resource Strategy

### Volume Mounts
```yaml
volumes:
- name: ssl-certificates
  hostPath:
    path: ./data/certificates
    type: DirectoryOrCreate
```

**Mount Pattern for Certificate Consumers**:
- **Mount Path**: `/data/ssl` (read-only)
- **Files Available**:
  - `cert.pem` - Server certificate
  - `privkey.pem` - Private key (mode 640)
  - `fullchain.pem` - Certificate + chain

### File Permissions Strategy
- **Certificate files**: 644 (readable by all services)
- **Private key**: 640 (readable by ssl-cert group)
- **Directory**: 755 (accessible by all)

## Startup Dependencies

### Service Boot Order
1. **Certificate Service** (foundation)
2. **DNS Service** (independent, can start in parallel)
3. **Apache Service** (waits for certificates)
4. **Mail Service** (waits for certificates)

### Health Check Dependencies
```bash
# Apache waits for certificate availability
initContainers:
- name: wait-for-certs
  image: localhost/podserve-harmony-certificates:latest
  command: ["/bin/bash", "-c"]
  args:
  - |
    until [ -f /data/ssl/cert.pem ] && [ -f /data/ssl/privkey.pem ]; do
      echo "Waiting for certificates..."
      sleep 5
    done
    echo "Certificates available"
  volumeMounts:
  - name: ssl-certificates
    mountPath: /data/ssl
```

## Failure Scenarios & Recovery

### Certificate Service Failure
**Impact**: 
- New certificate generation stops
- Existing certificates continue to work
- Certificate renewals fail

**Recovery Strategy**:
- Certificate service restart should not affect running services
- Existing certificate files persist in volumes
- Services continue with cached certificates

**Test Scenarios**:
- [ ] Certificate service restart during operation
- [ ] Certificate service failure with services running
- [ ] Certificate expiration handling

### Certificate Renewal Integration
**Strategy**: Background renewal with graceful service updates

```bash
# Certificate renewal workflow
1. Certificate service detects expiration (7 days before)
2. Generates new certificates in temporary location
3. Atomically replaces old certificates
4. Dependent services detect change and reload
```

**Integration Tests**:
- [ ] Certificate renewal without service interruption
- [ ] Services detect and reload new certificates
- [ ] Renewal failure fallback behavior

## Integration Test Specifications

### Test Environment Setup
```yaml
# integration-test-certificates.yaml
apiVersion: v1
kind: Pod
metadata:
  name: certificate-integration-test
spec:
  containers:
  - name: certificates
    image: localhost/podserve-harmony-certificates:latest
    volumeMounts:
    - name: test-certs
      mountPath: /data/state/certificates
      
  - name: test-consumer
    image: alpine:latest
    command: ["sleep", "300"]
    volumeMounts:
    - name: test-certs
      mountPath: /test/ssl
      readOnly: true
      
  volumes:
  - name: test-certs
    emptyDir: {}
```

### Test Plan: Certificate + Apache Integration

**Phase 4.1: Basic Integration**
- [ ] Deploy certificate service
- [ ] Deploy Apache with certificate volume mount
- [ ] Verify Apache can read certificate files
- [ ] Test HTTPS connection establishment
- [ ] Verify certificate validation

**Phase 4.2: Dynamic Scenarios**
- [ ] Certificate renewal during Apache operation
- [ ] Certificate service restart with Apache running
- [ ] Volume mount permission verification
- [ ] SSL configuration reload testing

**Phase 4.3: Failure Recovery**
- [ ] Apache behavior with missing certificates
- [ ] Certificate corruption scenarios
- [ ] Network isolation between services

## Next Service Planning: DNS

Since DNS doesn't require certificates, it can be developed in parallel:

**DNS Service Development Plan**:
- **Phase 1**: DNS service planning (bind9 or alternative)
- **Phase 2**: DNS service isolation testing
- **Phase 3**: DNS performance validation
- **Phase 4**: DNS integration with other services (reverse lookups, etc.)

**No blocking dependencies** between Certificate and DNS services.

## Integration Success Criteria

✅ **Certificate service provides**:
- Self-signed certificates for development
- Let's Encrypt certificates for production
- Automatic renewal workflows
- Shared volume access patterns

✅ **Integration patterns enable**:
- Zero-downtime certificate updates
- Secure certificate sharing between services
- Proper permission isolation
- Health check dependencies

✅ **Ready for downstream services**:
- Apache/Web services can consume certificates
- Mail services can use SSL/TLS
- Admin interfaces can enable HTTPS
- Monitoring can verify certificate status

## Phase 4 Completion Checklist

- [ ] Integration patterns documented
- [ ] Shared volume strategies defined
- [ ] Failure scenarios planned
- [ ] Test specifications created
- [ ] Next service dependencies identified
- [ ] Parallel development paths established

**Result**: Certificate service ready for production integration with clear patterns for all downstream SSL-dependent services.