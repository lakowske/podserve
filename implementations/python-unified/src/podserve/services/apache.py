"""Apache service implementation for PodServe."""

import os
import time
from pathlib import Path
from typing import List

from podserve.core.service import BaseService


class ApacheService(BaseService):
    """Apache web service."""
    
    def __init__(self, debug: bool = False):
        """Initialize Apache service."""
        super().__init__('apache', debug)
        self.apache_process = None
        self.start_time = time.time()
    
    def get_service_directories(self) -> List[str]:
        """Get Apache-specific directories to create."""
        return [
            self.config.get('APACHE_DOCUMENT_ROOT', '/data/web/html'),
            '/etc/apache2/sites-available',
            '/etc/apache2/sites-enabled',
            '/var/log/apache2',
        ]
    
    def get_required_config_vars(self) -> List[str]:
        """Get required configuration variables."""
        return ['APACHE_SERVER_NAME']
    
    def configure(self) -> bool:
        """Configure Apache service."""
        self.logger.info("Configuring Apache service")
        
        try:
            # Create document root with sample content
            self.create_document_root()
            
            # Configure main Apache virtual host
            if not self.configure_virtual_host():
                return False
            
            # Configure SSL if enabled
            if self.config.is_ssl_enabled():
                if not self.configure_ssl():
                    return False
            
            # Enable required Apache modules
            self.enable_apache_modules()
            
            self.logger.info("Apache service configuration completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Apache configuration failed: {e}")
            return False
    
    def create_document_root(self):
        """Create document root with sample content."""
        doc_root = Path(self.config.get('APACHE_DOCUMENT_ROOT', '/data/web/html'))
        doc_root.mkdir(parents=True, exist_ok=True)
        
        # Create a simple index.html if it doesn't exist
        index_file = doc_root / 'index.html'
        if not index_file.exists():
            server_name = self.config.get('APACHE_SERVER_NAME', 'localhost')
            index_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Welcome to {server_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        .status {{ background: #e8f5e8; padding: 20px; border-radius: 5px; }}
        .info {{ margin-top: 20px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to {server_name}</h1>
        <div class="status">
            <h2>✅ Apache is Running!</h2>
            <p>Your PodServe web server is successfully running.</p>
        </div>
        <div class="info">
            <h3>Server Information:</h3>
            <ul>
                <li><strong>Server Name:</strong> {server_name}</li>
                <li><strong>Document Root:</strong> {doc_root}</li>
                <li><strong>SSL Enabled:</strong> {'Yes' if self.config.is_ssl_enabled() else 'No'}</li>
            </ul>
        </div>
    </div>
</body>
</html>"""
            index_file.write_text(index_content)
            self.logger.info(f"Created sample index.html at {index_file}")
    
    def configure_virtual_host(self) -> bool:
        """Configure Apache virtual host."""
        try:
            # Prepare configuration context
            config_context = {
                'APACHE_SERVER_NAME': self.config.get('APACHE_SERVER_NAME', 'localhost'),
                'APACHE_DOCUMENT_ROOT': self.config.get('APACHE_DOCUMENT_ROOT', '/data/web/html'),
                'APACHE_SERVER_ADMIN': self.config.get('APACHE_SERVER_ADMIN', 'webmaster@localhost'),
            }
            
            # Render main virtual host configuration
            self.config.render_template(
                'apache-vhost.conf',
                '/etc/apache2/sites-available/000-default.conf',
                config_context
            )
            
            # Enable the site
            self.run_subprocess(['a2ensite', '000-default'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Virtual host configuration failed: {e}")
            return False
    
    def configure_ssl(self) -> bool:
        """Configure SSL virtual host."""
        try:
            # Prepare SSL configuration context
            ssl_context = {
                'APACHE_SERVER_NAME': self.config.get('APACHE_SERVER_NAME', 'localhost'),
                'APACHE_DOCUMENT_ROOT': self.config.get('APACHE_DOCUMENT_ROOT', '/data/web/html'),
                'APACHE_SERVER_ADMIN': self.config.get('APACHE_SERVER_ADMIN', 'webmaster@localhost'),
                'SSL_CERT_FILE': self.config.get_ssl_cert_path(),
                'SSL_KEY_FILE': self.config.get_ssl_key_path(),
            }
            
            # Add SSL chain file if available
            chain_path = self.config.get_ssl_chain_path()
            if chain_path:
                ssl_context['SSL_CHAIN_FILE'] = chain_path
            
            # Render SSL virtual host configuration
            self.config.render_template(
                'apache-ssl-vhost.conf',
                '/etc/apache2/sites-available/000-default-ssl.conf',
                ssl_context
            )
            
            # Enable SSL site
            self.run_subprocess(['a2ensite', '000-default-ssl'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"SSL configuration failed: {e}")
            return False
    
    def enable_apache_modules(self):
        """Enable required Apache modules."""
        modules = ['rewrite', 'headers']
        
        # Add SSL module if SSL is enabled
        if self.config.is_ssl_enabled():
            modules.append('ssl')
        
        for module in modules:
            self.run_subprocess(['a2enmod', module])
            self.logger.debug(f"Enabled Apache module: {module}")
    
    def start_service(self) -> bool:
        """Start Apache service."""
        self.logger.info("Starting Apache")
        
        try:
            # Start Apache in foreground mode
            self.apache_process = self.run_subprocess([
                'apache2ctl', '-DFOREGROUND'
            ], capture_output=True, background=True)
            
            if self.apache_process:
                self.logger.info(f"Apache started with PID {self.apache_process.pid}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting Apache: {e}")
            return False
    
    def stop_service(self) -> bool:
        """Stop Apache service."""
        if self.apache_process:
            try:
                self.apache_process.terminate()
                self.apache_process.wait(timeout=5)
                return True
            except Exception:
                self.apache_process.kill()
                return True
        return True
    
    def health_check(self) -> bool:
        """Perform Apache health check."""
        try:
            from podserve.core.utils import check_service_listening
            
            # Check HTTP port (essential)
            if not check_service_listening(80):
                self.logger.warning("HTTP port 80 not responding")
                return False
            
            # Check HTTPS port if SSL is enabled
            if self.config.is_ssl_enabled():
                if not check_service_listening(443):
                    self.logger.warning("HTTPS port 443 not responding")
                    return False
            
            # Optional: Check if our managed process is still running
            if self.apache_process and self.apache_process.poll() is not None:
                self.logger.debug("Managed Apache process has exited (service may be externally managed)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False