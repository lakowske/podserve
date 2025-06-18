# DNS Service Implementation Plan

## Overview

Implement a DNS forwarding service in Python that manages BIND9 configuration and provides caching DNS resolution with configurable upstream servers.

## Python Implementation

### Service Class (services/dns.py)

```python
class DNSService(BaseService):
    def __init__(self):
        super().__init__("dns")
        self.bind_dir = "/etc/bind"
        self.cache_dir = "/var/cache/bind"
        self.named_bin = "/usr/sbin/named"
        
    def configure(self):
        # Parse DNS forwarders from environment
        # Generate BIND configuration from templates
        # Validate configuration
        
    def start(self):
        # Configure BIND
        # Validate config
        # Start named process
```

### Configuration Management

#### 1. Parse Forwarders

```python
def parse_forwarders(self):
    forwarders = os.environ.get("DNS_FORWARDERS", "8.8.8.8;8.8.4.4")
    return [f.strip() for f in forwarders.split(";")]
```

#### 2. Generate BIND Configuration

```python
def generate_config(self):
    config_template = """
options {
    directory "/var/cache/bind";
    
    forwarders {
        {% for forwarder in forwarders %}
        {{ forwarder }};
        {% endfor %}
    };
    
    forward only;
    
    dnssec-validation {{ dnssec_enabled }};
    
    listen-on { any; };
    listen-on-v6 { any; };
    
    allow-query { any; };
    
    recursion yes;
    allow-recursion { any; };
    
    querylog yes;
};
"""
    
    template = Template(config_template)
    config = template.render(
        forwarders=self.parse_forwarders(),
        dnssec_enabled=os.environ.get("DNSSEC_ENABLED", "no")
    )
    
    with open(f"{self.bind_dir}/named.conf.options", "w") as f:
        f.write(config)
```

#### 3. Configuration Validation

```python
def validate_config(self):
    try:
        subprocess.run(
            ["named-checkconf"], 
            check=True,
            capture_output=True,
            text=True
        )
        self.logger.info("BIND configuration validated successfully")
    except subprocess.CalledProcessError as e:
        self.logger.error(f"Configuration validation failed: {e.stderr}")
        raise
```

### Process Management

```python
def start(self):
    # Set up directories and permissions
    self.setup_directories()
    
    # Generate configuration
    self.generate_config()
    
    # Validate
    self.validate_config()
    
    # Start BIND
    self.logger.info(f"Starting BIND with forwarders: {self.parse_forwarders()}")
    
    # Execute named directly
    os.execvp(self.named_bin, [
        self.named_bin,
        "-g",  # Run in foreground
        "-u", "bind"  # Run as bind user
    ])
```

### Health Check Implementation

```python
def health_check(self):
    """Verify DNS resolution is working"""
    import dns.resolver
    
    try:
        # Create resolver pointing to localhost
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['127.0.0.1']
        resolver.timeout = 5
        
        # Try to resolve a known domain
        answers = resolver.resolve('google.com', 'A')
        
        if answers:
            return {"status": "healthy", "resolved": str(answers[0])}
        else:
            return {"status": "unhealthy", "error": "No answers"}
            
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Advanced Features

#### 1. Dynamic Forwarder Updates

```python
def update_forwarders(self, new_forwarders):
    """Update forwarders without restart using rndc"""
    # Generate new config
    os.environ["DNS_FORWARDERS"] = ";".join(new_forwarders)
    self.generate_config()
    
    # Reload BIND
    subprocess.run(["rndc", "reload"], check=True)
```

#### 2. Query Logging

```python
def enable_query_logging(self):
    """Enable detailed query logging"""
    logging_config = """
logging {
    channel query_log {
        file "/data/logs/dns/query.log" versions 3 size 5m;
        severity info;
        print-time yes;
        print-category yes;
    };
    
    category queries { query_log; };
};
"""
    
    with open(f"{self.bind_dir}/named.conf.logging", "w") as f:
        f.write(logging_config)
```

#### 3. Statistics Collection

```python
def get_statistics(self):
    """Collect DNS server statistics"""
    try:
        output = subprocess.check_output(
            ["rndc", "stats"],
            text=True
        )
        
        # Parse statistics file
        stats_file = "/var/cache/bind/named.stats"
        if os.path.exists(stats_file):
            with open(stats_file) as f:
                return self.parse_stats(f.read())
                
    except Exception as e:
        self.logger.error(f"Failed to get statistics: {e}")
        return {}
```

## Implementation Steps

1. Create DNSService class extending BaseService
2. Implement forwarder parsing from environment
3. Create BIND configuration template and generator
4. Add configuration validation using named-checkconf
5. Implement process lifecycle management
6. Add health check with DNS resolution test
7. Optional: Add dynamic configuration updates and statistics

## Environment Variables

- `DNS_FORWARDERS`: Semicolon-separated list of upstream DNS servers
- `DNSSEC_ENABLED`: Enable DNSSEC validation (yes/no)

## Directory Structure

```
/etc/bind/
├── named.conf
├── named.conf.options    # Generated config
└── named.conf.logging    # Optional logging config

/var/cache/bind/          # BIND cache directory
/data/logs/dns/          # Query logs (optional)
```

## Dockerfile Changes

```dockerfile
FROM localhost/podserve-base:latest

# Install BIND (as before)
...

# Additional Python dependencies
RUN pip3 install --break-system-packages dnspython

# Run Python service
CMD ["python3", "-m", "podserve.services.dns"]
```

## Testing

```python
# Test DNS resolution through the service
def test_dns_forwarding():
    import socket
    
    # Test resolution
    result = socket.gethostbyname('google.com')
    assert result  # Should return an IP address
    
    # Test forwarder configuration
    service = DNSService()
    forwarders = service.parse_forwarders()
    assert "8.8.8.8" in forwarders  # Default Google DNS
```