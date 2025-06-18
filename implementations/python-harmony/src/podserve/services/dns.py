"""DNS service for PodServe-Harmony.

This service provides DNS resolution for PodServe infrastructure using BIND9,
enabling local domain resolution and external DNS forwarding.

Features:
- Local domain resolution (lab.sethlakowske.com)
- External DNS forwarding
- Dynamic zone file management
- BIND9 process lifecycle management
- Health check via DNS queries
"""

import os
import sys
import time
import subprocess
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import tempfile

from podserve.core.service import BaseService


class DNSService(BaseService):
    """DNS service providing local and recursive DNS resolution."""
    
    def __init__(self, debug: bool = False):
        """Initialize the DNS service.
        
        Args:
            debug: Whether to enable debug logging
        """
        # Set up directory paths before calling super().__init__()
        # since super().__init__() calls create_directories() which needs these
        self.dns_dir = Path("/data/state/dns")
        self.config_dir = Path("/data/config/dns")
        self.zones_dir = self.dns_dir / "zones"
        self.cache_dir = self.dns_dir / "cache"
        
        super().__init__("dns", debug)
        
        # DNS Configuration  
        self.domain = self.config.get("DNS_DOMAIN", "lab.sethlakowske.com")
        self.admin_email = self.config.get("DNS_ADMIN_EMAIL", f"admin@{self.domain}")
        self.forwarders = self.config.get("DNS_FORWARDERS", "8.8.8.8;1.1.1.1").split(";")
        self.listen_address = self.config.get("DNS_LISTEN_ADDRESS", "0.0.0.0")
        self.allow_query = self.config.get("DNS_ALLOW_QUERY", "any")
        self.allow_recursion = self.config.get("DNS_ALLOW_RECURSION", "yes")
        
        # BIND9 process tracking
        self.named_process = None
        self.named_conf_path = self.config_dir / "named.conf"
        self.zone_file_path = self.zones_dir / f"{self.domain}.zone"
        
        self.logger.info(f"DNS service initialized for domain: {self.domain}")
        self.logger.info(f"Forwarders: {', '.join(self.forwarders)}")
        
    def get_service_directories(self) -> List[str]:
        """Get service-specific directories to create."""
        return [
            str(self.dns_dir),
            str(self.config_dir),
            str(self.zones_dir),
            str(self.cache_dir)
        ]
    
    def get_required_config_vars(self) -> List[str]:
        """Get required configuration variables."""
        return [
            "DNS_DOMAIN"
        ]
    
    def configure(self) -> bool:
        """Configure the DNS service by generating BIND9 configuration files."""
        try:
            # Generate main BIND9 configuration
            if not self._generate_named_conf():
                return False
            
            # Generate zone file for our domain
            if not self._generate_zone_file():
                return False
            
            # Set proper permissions
            self._set_file_permissions()
            
            self.logger.info("DNS service configuration completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure DNS service: {e}")
            return False
    
    def _generate_named_conf(self) -> bool:
        """Generate the main BIND9 configuration file."""
        try:
            named_conf_content = f"""
// BIND9 Configuration for PodServe-Harmony DNS Service
// Generated automatically - do not edit manually

options {{
    directory "/data/state/dns/cache";
    
    // Listen on all interfaces
    listen-on {{ {self.listen_address}; }};
    listen-on-v6 {{ any; }};
    
    // DNS query permissions
    allow-query {{ {self.allow_query}; }};
    recursion {self.allow_recursion};
    
    // Forwarders for external queries
    forwarders {{
        {'; '.join(self.forwarders)};
    }};
    
    // Security settings
    dnssec-validation auto;
    
    // Logging
    pid-file "/data/state/dns/named.pid";
}};

// Logging configuration
logging {{
    channel default_debug {{
        file "/data/logs/named.log";
        severity debug;
        print-time yes;
        print-category yes;
        print-severity yes;
    }};
    category default {{ default_debug; }};
}};

// Root hints
zone "." {{
    type hint;
    file "/usr/share/dns/root.hints";
}};

// Local zones (only if not conflicting with our domain)
{'' if self.domain == 'localhost' else '''zone "localhost" {
    type master;
    file "/etc/bind/db.local";
};

'''}zone "127.in-addr.arpa" {{
    type master;
    file "/etc/bind/db.127";
}};

zone "0.in-addr.arpa" {{
    type master;
    file "/etc/bind/db.0";
}};

zone "255.in-addr.arpa" {{
    type master;
    file "/etc/bind/db.255";
}};

// Our domain zone
zone "{self.domain}" {{
    type master;
    file "{self.zone_file_path}";
    allow-update {{ none; }};
}};
"""
            
            with open(self.named_conf_path, 'w') as f:
                f.write(named_conf_content)
            
            self.logger.debug(f"Generated named.conf: {self.named_conf_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate named.conf: {e}")
            return False
    
    def _generate_zone_file(self) -> bool:
        """Generate the zone file for our domain."""
        try:
            # Get current timestamp for serial number
            serial = datetime.now().strftime("%Y%m%d01")
            
            # Get IP address for A records (default to localhost for development)
            ip_address = self.config.get("DNS_IP_ADDRESS", "127.0.0.1")
            
            zone_content = f"""
; Zone file for {self.domain}
; Generated automatically - do not edit manually

$TTL 86400
$ORIGIN {self.domain}.

@   IN  SOA {self.domain}. {self.admin_email.replace('@', '.')}. (
        {serial}    ; Serial number
        3600        ; Refresh (1 hour)
        900         ; Retry (15 minutes)
        1209600     ; Expire (2 weeks)
        86400       ; Minimum TTL (1 day)
)

; Name server records
@           IN  NS      {self.domain}.

; A records
@           IN  A       {ip_address}
mail        IN  A       {ip_address}
www         IN  A       {ip_address}
admin       IN  A       {ip_address}
api         IN  A       {ip_address}

; CNAME records
smtp        IN  CNAME   mail.{self.domain}.
imap        IN  CNAME   mail.{self.domain}.
pop3        IN  CNAME   mail.{self.domain}.

; MX record
@           IN  MX  10  mail.{self.domain}.

; TXT records
@           IN  TXT     "v=spf1 mx ~all"
_dmarc      IN  TXT     "v=DMARC1; p=none; rua=mailto:{self.admin_email}"
"""
            
            with open(self.zone_file_path, 'w') as f:
                f.write(zone_content)
            
            self.logger.debug(f"Generated zone file: {self.zone_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate zone file: {e}")
            return False
    
    def _set_file_permissions(self):
        """Set appropriate permissions for DNS configuration files."""
        try:
            # named.conf should be readable by bind
            os.chmod(str(self.named_conf_path), 0o644)
            
            # Zone files should be readable by bind
            os.chmod(str(self.zone_file_path), 0o644)
            
            # Cache directory should be writable by bind
            os.chmod(str(self.cache_dir), 0o755)
            
            self.logger.debug("Set file permissions for DNS configuration")
            
        except Exception as e:
            self.logger.warning(f"Failed to set file permissions: {e}")
    
    def start_service(self) -> bool:
        """Start the BIND9 DNS service."""
        try:
            # Check if BIND9 is already running
            if self.named_process and self.named_process.poll() is None:
                self.logger.info("BIND9 is already running")
                return True
            
            # Start BIND9 with our configuration
            cmd = [
                "named",
                "-c", str(self.named_conf_path),
                "-f",  # Run in foreground
                "-g"   # Log to stderr
                # Note: Not using -u bind since we're in a developer container
            ]
            
            self.logger.info(f"Starting BIND9: {' '.join(cmd)}")
            
            self.named_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give BIND9 a moment to start
            time.sleep(2)
            
            # Check if process started successfully
            if self.named_process.poll() is None:
                self.logger.info("BIND9 started successfully")
                return True
            else:
                # Process exited, get error output
                stdout, stderr = self.named_process.communicate()
                self.logger.error(f"BIND9 failed to start: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start BIND9: {e}")
            return False
    
    def stop_service(self) -> bool:
        """Stop the BIND9 DNS service."""
        try:
            if self.named_process and self.named_process.poll() is None:
                self.logger.info("Stopping BIND9")
                
                # Send SIGTERM for graceful shutdown
                self.named_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.named_process.wait(timeout=10)
                    self.logger.info("BIND9 stopped gracefully")
                except subprocess.TimeoutExpired:
                    self.logger.warning("BIND9 did not stop gracefully, forcing kill")
                    self.named_process.kill()
                    self.named_process.wait()
                
                self.named_process = None
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop BIND9: {e}")
            return False
    
    def health_check(self) -> bool:
        """Perform health check for the DNS service."""
        try:
            # Check if BIND9 process is running
            if not self.named_process or self.named_process.poll() is not None:
                self.logger.warning("BIND9 process is not running")
                return False
            
            # Test DNS resolution using dig
            test_queries = [
                # Test our domain resolution
                (self.domain, "A"),
                # Test external resolution (forwarding)
                ("google.com", "A")
            ]
            
            for domain, record_type in test_queries:
                if not self._test_dns_query(domain, record_type):
                    return False
            
            self.logger.debug("DNS service health check passed")
            return True
            
        except Exception as e:
            self.logger.error(f"DNS health check failed: {e}")
            return False
    
    def _test_dns_query(self, domain: str, record_type: str = "A") -> bool:
        """Test a DNS query against our service."""
        try:
            # Use dig to test DNS resolution
            cmd = [
                "dig", 
                f"@{self.listen_address}",
                "-p", "53",
                domain,
                record_type,
                "+short",
                "+time=5"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                self.logger.debug(f"DNS query successful: {domain} {record_type} -> {result.stdout.strip()}")
                return True
            else:
                self.logger.warning(f"DNS query failed: {domain} {record_type} - {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"DNS query timed out: {domain} {record_type}")
            return False
        except Exception as e:
            self.logger.warning(f"DNS query error: {domain} {record_type} - {e}")
            return False
    
    def reload_zones(self) -> bool:
        """Reload zone files without restarting BIND9."""
        try:
            if not self.named_process or self.named_process.poll() is not None:
                self.logger.error("Cannot reload zones: BIND9 is not running")
                return False
            
            # Send SIGHUP to reload configuration
            self.named_process.send_signal(signal.SIGHUP)
            self.logger.info("Sent reload signal to BIND9")
            
            # Give it a moment to reload
            time.sleep(1)
            
            # Test that service is still healthy
            return self.health_check()
            
        except Exception as e:
            self.logger.error(f"Failed to reload zones: {e}")
            return False
    
    def add_dns_record(self, name: str, record_type: str, value: str) -> bool:
        """Add a DNS record to the zone file (simplified implementation)."""
        try:
            # This is a basic implementation - in production you'd want
            # proper zone file parsing and manipulation
            record_line = f"{name.ljust(12)} IN  {record_type.ljust(6)} {value}\n"
            
            with open(self.zone_file_path, 'a') as f:
                f.write(record_line)
            
            self.logger.info(f"Added DNS record: {name} {record_type} {value}")
            
            # Reload zones to apply changes
            return self.reload_zones()
            
        except Exception as e:
            self.logger.error(f"Failed to add DNS record: {e}")
            return False