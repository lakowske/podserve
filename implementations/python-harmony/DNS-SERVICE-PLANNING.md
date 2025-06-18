# DNS Service Planning - Phase 1

**Service**: DNS Service  
**Implementation**: python-harmony  
**Date**: 2025-06-18  
**Dependencies**: None (Independent foundation service)

## Service Overview

### Purpose
Provide DNS resolution services for PodServe infrastructure, enabling:
- Local domain resolution (`lab.sethlakowske.com`)
- Internal service discovery
- External DNS forwarding
- Development-friendly domain management

### Key Requirements

**Functional Requirements**:
- Resolve `lab.sethlakowske.com` and subdomains
- Forward external queries to upstream DNS
- Support A, AAAA, CNAME, MX, TXT records
- Dynamic record management via API/config
- Health check endpoint

**Performance Requirements**:
- Query response time: <50ms for local records
- Startup time: <5 seconds
- Memory usage: <100MB
- Handle 1000+ queries/second

**Integration Requirements**:
- No certificate dependencies (DNS is unencrypted)
- Container-friendly configuration
- Persistent zone file storage
- Python-based management interface

## DNS Server Technology Research

### Option 1: BIND9 (Berkeley Internet Name Domain)
**Pros**:
- Industry standard, battle-tested
- Comprehensive DNS feature support
- Excellent documentation
- Debian package available

**Cons**:
- Complex configuration syntax
- Large memory footprint
- Requires separate management tools

**Configuration Example**:
```bind
zone "lab.sethlakowske.com" {
    type master;
    file "/etc/bind/zones/lab.sethlakowske.com";
};
```

### Option 2: Unbound (Validating, recursive, caching DNS resolver)
**Pros**:
- Lightweight and secure
- Built-in DNSSEC support
- Simple configuration
- Good performance

**Cons**:
- Primarily a resolver (not authoritative)
- Limited zone management features
- Less comprehensive than BIND

### Option 3: PowerDNS
**Pros**:
- Modern architecture
- REST API for management
- Database backend support
- Good performance

**Cons**:
- More complex setup
- Additional dependencies

### Option 4: CoreDNS
**Pros**:
- Cloud-native design
- Plugin architecture
- Kubernetes integration
- Go-based (single binary)

**Cons**:
- Different from traditional DNS servers
- May be overkill for simple use case

### Recommendation: BIND9

**Selected**: BIND9 for the following reasons:
1. **Proven reliability** - Industry standard
2. **Complete feature set** - Authoritative + recursive
3. **Debian integration** - Easy container setup
4. **Documentation** - Extensive resources available
5. **Management flexibility** - Zone files + rndc control

## DNS Service Architecture

### Container Design
```dockerfile
FROM localhost/podserve-harmony-base:latest

# Install BIND9 and utilities
RUN apt-get update && apt-get install -y \
    bind9 \
    bind9utils \
    bind9-doc \
    dnsutils

# Python DNS management layer
RUN pip install dnspython

# Service structure
/data/state/dns/          # Zone files, cache
/data/config/dns/         # BIND configuration
/opt/src/podserve/services/dns.py  # Python management
```

### Service Architecture
```
DNS Service Components:
├── BIND9 Process (DNS Server)
│   ├── named.conf (main config)
│   ├── zones/ (zone files)
│   └── cache/ (resolver cache)
├── Python Management Layer
│   ├── DNSService (BaseService implementation)
│   ├── Zone file management
│   ├── BIND9 process control
│   └── Health checks
└── Configuration
    ├── Domain: lab.sethlakowske.com
    ├── Upstream: 8.8.8.8, 1.1.1.1
    └── Listen: 0.0.0.0:53
```

### Zone File Strategy
```bind
; lab.sethlakowske.com zone file
$TTL 86400
@   IN  SOA lab.sethlakowske.com. admin.lab.sethlakowske.com. (
        2025061801  ; Serial
        3600        ; Refresh
        900         ; Retry
        1209600     ; Expire
        86400       ; Minimum TTL
)

; Name servers
@           IN  NS      lab.sethlakowske.com.

; A records
@           IN  A       192.168.1.100
mail        IN  A       192.168.1.100
www         IN  A       192.168.1.100
admin       IN  A       192.168.1.100

; CNAME records
api         IN  CNAME   lab.sethlakowske.com.

; MX record
@           IN  MX  10  mail.lab.sethlakowske.com.
```

## Implementation Plan

### Phase 1: Planning ✅ (Current)
- [x] Research DNS server options
- [x] Define service requirements
- [x] Design architecture
- [ ] Complete implementation planning

### Phase 2: Isolation Development
**Tasks**:
1. Create DNS service Python class
2. Implement BaseService abstract methods
3. BIND9 configuration generation
4. Zone file management
5. Process lifecycle management
6. Health check implementation

**Validation**:
- DNS service starts successfully
- Resolves local domain queries
- Forwards external queries
- Health checks pass
- Zone file persistence

### Phase 3: Performance Testing
**Metrics to validate**:
- Startup time: <5 seconds
- Query response: <50ms local, <200ms external
- Memory usage: <100MB
- Query throughput: 1000+/second

### Phase 4: Integration Planning
**Integration patterns**:
- Independent service (no dependencies)
- Other services use DNS for name resolution
- Web services point to DNS for domain resolution
- Mail services use DNS for MX lookups

## Service Directory Structure

```
implementations/python-harmony/
├── src/podserve/services/
│   └── dns.py                 # DNS service implementation
├── docker/
│   └── dns/
│       ├── Dockerfile.developer
│       ├── named.conf.template
│       └── entrypoint.sh
├── tests/
│   ├── validate-dns.sh
│   └── dns-test-queries.txt
└── deploy/
    └── dns-dev.yaml
```

## Configuration Strategy

### Environment Variables
```bash
# DNS Configuration
DNS_DOMAIN=lab.sethlakowske.com
DNS_ADMIN_EMAIL=admin@lab.sethlakowske.com
DNS_FORWARDERS=8.8.8.8;1.1.1.1
DNS_LISTEN_ADDRESS=0.0.0.0
DNS_ALLOW_QUERY=any
DNS_ALLOW_RECURSION=yes

# Service Configuration
LOG_LEVEL=DEBUG
```

### Python Management Interface
```python
class DNSService(BaseService):
    def __init__(self, debug=False):
        # DNS-specific paths before super().__init__()
        self.dns_dir = Path("/data/state/dns")
        self.config_dir = Path("/data/config/dns")
        self.zones_dir = self.dns_dir / "zones"
        super().__init__("dns", debug)
    
    def configure(self) -> bool:
        # Generate named.conf
        # Create zone files
        # Set up logging
        
    def start_service(self) -> bool:
        # Start BIND9 with generated config
        
    def stop_service(self) -> bool:
        # Stop BIND9 gracefully
        
    def health_check(self) -> bool:
        # Query DNS service
        # Check BIND9 process
```

## Testing Strategy

### Unit Tests
- Zone file generation
- Configuration templating
- Process management
- Health check logic

### Integration Tests
- DNS query resolution
- Recursive forwarding
- Zone file updates
- Service lifecycle

### Performance Tests
- Query response times
- Concurrent query handling
- Memory usage under load
- Startup performance

## Success Criteria

**Phase 1 Complete When**:
- [ ] DNS server technology selected (BIND9)
- [ ] Service architecture documented
- [ ] Implementation plan detailed
- [ ] Directory structure created
- [ ] Configuration strategy defined

**Ready for Phase 2**: DNS service isolation development

## Risk Assessment

**Low Risk**:
- No external dependencies (certificates)
- Well-understood DNS protocols
- Proven BIND9 technology

**Medium Risk**:
- BIND9 configuration complexity
- Process management in containers
- Zone file syntax correctness

**Mitigation**:
- Start with minimal configuration
- Use configuration templates
- Comprehensive testing with dig/nslookup
- Reference existing BIND9 setups

## Next Steps

1. Complete Phase 1 by setting up directory structure
2. Begin Phase 2: DNS service implementation
3. Follow same systematic validation as certificate service
4. Use lessons learned from certificate service (volume mounts, user namespaces, etc.)

**Target**: Complete DNS service Phases 1-4 within same timeframe as certificates, leveraging proven development patterns.