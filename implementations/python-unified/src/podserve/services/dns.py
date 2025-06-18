"""DNS service implementation for PodServe."""

import time
from typing import List
from pathlib import Path

from podserve.core.service import BaseService


class DNSService(BaseService):
    """BIND9 DNS service."""
    
    def __init__(self, debug: bool = False):
        """Initialize DNS service."""
        super().__init__('dns', debug)
        self.bind_process = None
        self.start_time = time.time()
    
    def get_service_directories(self) -> List[str]:
        """Get DNS-specific directories to create."""
        return [
            '/etc/bind/zones',
            '/var/cache/bind',
            '/var/lib/bind',
            '/var/log/bind',
        ]
    
    def get_required_config_vars(self) -> List[str]:
        """Get required configuration variables."""
        return [
            'DNS_DOMAIN',
            'DNS_FORWARDERS',
            'WEB_SERVER_IP',
            'MAIL_SERVER_IP'
        ]
    
    def configure(self) -> bool:
        """Configure DNS service."""
        self.logger.info("Configuring BIND9 DNS service")
        
        try:
            # Configure main BIND configuration
            if not self.configure_bind_main():
                return False
            
            # Configure zone files
            if not self.configure_zones():
                return False
            
            # Set proper permissions
            self.set_bind_permissions()
            
            self.logger.info("BIND9 DNS service configuration completed")
            return True
            
        except Exception as e:
            self.logger.error(f"DNS configuration failed: {e}")
            return False
    
    def configure_bind_main(self) -> bool:
        """Configure main BIND configuration."""
        try:
            # Prepare configuration context
            config_context = {
                'DNS_DOMAIN': self.config.get('DNS_DOMAIN', 'lab.localhost'),
                'DNS_FORWARDERS': self.config.get('DNS_FORWARDERS', '8.8.8.8; 8.8.4.4'),
            }
            
            # Render main named.conf
            self.config.render_template(
                'named.conf',
                '/etc/bind/named.conf',
                config_context
            )
            
            # Render named.conf.local with zone definitions
            self.config.render_template(
                'named.conf.local',
                '/etc/bind/named.conf.local',
                config_context
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"BIND main configuration failed: {e}")
            return False
    
    def configure_zones(self) -> bool:
        """Configure DNS zone files."""
        try:
            domain = self.config.get('DNS_DOMAIN', 'lab.localhost')
            web_ip = self.config.get('WEB_SERVER_IP', '127.0.0.1')
            mail_ip = self.config.get('MAIL_SERVER_IP', '127.0.0.1')
            
            # Prepare zone context
            zone_context = {
                'DNS_DOMAIN': domain,
                'WEB_SERVER_IP': web_ip,
                'MAIL_SERVER_IP': mail_ip,
                'SERIAL': int(time.time()),  # Use timestamp as serial
            }
            
            # Render forward zone file
            zone_file = f'/etc/bind/zones/db.{domain}'
            self.config.render_template(
                'zone.forward',
                zone_file,
                zone_context
            )
            
            # Render reverse zone file (for 127.0.0.x)
            reverse_zone_file = '/etc/bind/zones/db.127'
            self.config.render_template(
                'zone.reverse',
                reverse_zone_file,
                zone_context
            )
            
            # Render RPZ zone file
            rpz_zone_file = '/etc/bind/zones/db.rpz'
            self.config.render_template(
                'db.rpz',
                rpz_zone_file,
                zone_context
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Zone configuration failed: {e}")
            return False
    
    def set_bind_permissions(self):
        """Set proper permissions for BIND files."""
        try:
            # Set ownership for BIND directories
            bind_dirs = [
                '/etc/bind',
                '/var/cache/bind',
                '/var/lib/bind',
                '/var/log/bind'
            ]
            
            for bind_dir in bind_dirs:
                if Path(bind_dir).exists():
                    self.run_subprocess(['chown', '-R', 'bind:bind', bind_dir])
                    self.run_subprocess(['chmod', '-R', '755', bind_dir])
            
            # Set specific permissions for zone files
            zone_dir = Path('/etc/bind/zones')
            if zone_dir.exists():
                for zone_file in zone_dir.glob('*'):
                    self.run_subprocess(['chmod', '644', str(zone_file)])
                
        except Exception as e:
            self.logger.warning(f"Could not set BIND permissions: {e}")
    
    def start_service(self) -> bool:
        """Start BIND9 service."""
        self.logger.info("Starting BIND9")
        
        try:
            # Start BIND in foreground mode with logging and proper user
            self.logger.info("Running command: named -f -g -c /etc/bind/named.conf -u bind")
            self.bind_process = self.run_subprocess([
                'named', '-f', '-g', '-c', '/etc/bind/named.conf', '-u', 'bind'
            ], capture_output=True, background=True)
            
            if self.bind_process:
                self.logger.info(f"BIND9 started with PID {self.bind_process.pid}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting BIND9: {e}")
            return False
    
    def stop_service(self) -> bool:
        """Stop DNS service."""
        if self.bind_process:
            try:
                self.bind_process.terminate()
                self.bind_process.wait(timeout=5)
                return True
            except Exception:
                self.bind_process.kill()
                return True
        return True
    
    def health_check(self) -> bool:
        """Perform DNS health check."""
        try:
            from podserve.core.utils import check_service_listening
            
            # Check DNS port (essential)
            if not check_service_listening(53):
                self.logger.warning("DNS port 53 not responding")
                return False
            
            # Optional: Check if our managed process is still running
            if self.bind_process and self.bind_process.poll() is not None:
                self.logger.debug("Managed BIND9 process has exited (service may be externally managed)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False