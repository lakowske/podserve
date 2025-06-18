"""Configuration management for PodServe services."""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
import logging


class ConfigManager:
    """Manages configuration loading, defaults, and template rendering."""
    
    def __init__(self, service_name: str, template_dir: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            service_name: Name of the service
            template_dir: Directory containing Jinja2 templates
        """
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        
        # Set up template environment
        if template_dir is None:
            template_dir = Path(__file__).parent.parent / "templates" / service_name
        
        self.template_dir = template_dir
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)) if template_dir.exists() else None,
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Configuration storage
        self.config = {}
        self.load_environment_variables()
    
    def load_environment_variables(self):
        """Load configuration from environment variables."""
        # Common environment variables for all services
        common_defaults = {
            'PODSERVE_USER': 'podserve',
            'PODSERVE_UID': '1000',
            'PODSERVE_GID': '1000',
            'LOG_LEVEL': 'INFO',
            'DATA_DIR': '/data',
            'CONFIG_DIR': '/data/config',
            'LOGS_DIR': '/data/logs',
            'STATE_DIR': '/data/state',
            'SSL_ENABLED': 'auto',
            'SSL_CERT_DIR': '/data/state/certificates',
        }
        
        # Service-specific defaults
        service_defaults = self.get_service_defaults()
        
        # Merge defaults
        all_defaults = {**common_defaults, **service_defaults}
        
        # Load from environment with defaults
        for key, default_value in all_defaults.items():
            self.config[key] = os.environ.get(key, default_value)
        
        # Load any additional environment variables
        for key, value in os.environ.items():
            if key not in self.config:
                self.config[key] = value
        
        self.logger.debug(f"Loaded configuration: {len(self.config)} variables")
    
    def get_service_defaults(self) -> Dict[str, str]:
        """Get service-specific default configuration values."""
        defaults = {}
        
        if self.service_name == 'mail':
            defaults.update({
                'MAIL_SERVER_NAME': 'mail.localhost',
                'MAIL_DOMAIN': 'localhost',
                'MAIL_DATA_DIR': '/var/mail/vhosts',
                'POSTFIX_CONFIG_DIR': '/etc/postfix',
                'DOVECOT_CONFIG_DIR': '/etc/dovecot',
            })
        
        elif self.service_name == 'apache':
            defaults.update({
                'APACHE_SERVER_NAME': 'localhost',
                'APACHE_SERVER_ADMIN': 'admin@localhost',
                'APACHE_DOCUMENT_ROOT': '/data/web/html',
                'APACHE_CONFIG_DIR': '/etc/apache2',
                'WEBDAV_ENABLED': 'false',
                'GITWEB_ENABLED': 'false',
            })
        
        elif self.service_name == 'dns':
            defaults.update({
                'DNS_DOMAIN': 'localhost',
                'DNS_SERVER_NAME': 'ns.localhost',
                'DNS_FORWARDERS': '8.8.8.8;1.1.1.1',
                'DNSSEC_ENABLED': 'true',
                'BIND_CONFIG_DIR': '/etc/bind',
            })
        
        elif self.service_name == 'certbot':
            defaults.update({
                'CERT_MODE': 'self-signed',
                'CERT_EMAIL': 'admin@localhost',
                'CERT_DOMAINS': 'localhost',
                'CERT_WEBROOT': '/data/web/html',
            })
        
        return defaults
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
    
    def load_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Loaded configuration data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.logger.warning(f"Configuration file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix.lower() in ['.yml', '.yaml']:
                    data = yaml.safe_load(f)
                elif file_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    self.logger.error(f"Unsupported file format: {file_path}")
                    return {}
            
            self.logger.info(f"Loaded configuration from {file_path}")
            return data or {}
            
        except Exception as e:
            self.logger.error(f"Error loading configuration file {file_path}: {e}")
            return {}
    
    def render_template(self, template_name: str, output_path: Optional[Union[str, Path]] = None,
                       additional_vars: Optional[Dict[str, Any]] = None) -> str:
        """Render a Jinja2 template with current configuration.
        
        Args:
            template_name: Name of the template file
            output_path: Optional path to write rendered template
            additional_vars: Additional variables for template rendering
            
        Returns:
            Rendered template content
        """
        if self.jinja_env.loader is None:
            raise ValueError(f"No template directory configured for {self.service_name}")
        
        try:
            template = self.jinja_env.get_template(template_name)
        except Exception as e:
            self.logger.error(f"Error loading template {template_name}: {e}")
            raise
        
        # Prepare template variables
        template_vars = self.config.copy()
        if additional_vars:
            template_vars.update(additional_vars)
        
        # Add helper functions
        template_vars.update({
            'ssl_enabled': self.is_ssl_enabled(),
            'ssl_cert_exists': self.ssl_cert_exists(),
            'format_forwarders': self.format_dns_forwarders,
            'escape_dollar': self.escape_dollar_for_bind,
        })
        
        try:
            rendered = template.render(**template_vars)
            
            # Write to file if output path specified
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w') as f:
                    f.write(rendered)
                
                self.logger.info(f"Rendered template {template_name} to {output_path}")
            
            return rendered
            
        except Exception as e:
            self.logger.error(f"Error rendering template {template_name}: {e}")
            raise
    
    def render_string_template(self, template_string: str, 
                              additional_vars: Optional[Dict[str, Any]] = None) -> str:
        """Render a template from string.
        
        Args:
            template_string: Template content as string
            additional_vars: Additional variables for template rendering
            
        Returns:
            Rendered template content
        """
        template = Template(template_string)
        
        # Prepare template variables
        template_vars = self.config.copy()
        if additional_vars:
            template_vars.update(additional_vars)
        
        return template.render(**template_vars)
    
    def is_ssl_enabled(self) -> bool:
        """Check if SSL is enabled for this service."""
        ssl_enabled = self.get('SSL_ENABLED', 'auto').lower()
        
        if ssl_enabled == 'true':
            return True
        elif ssl_enabled == 'false':
            return False
        elif ssl_enabled == 'auto':
            return self.ssl_cert_exists()
        else:
            return False
    
    def ssl_cert_exists(self) -> bool:
        """Check if SSL certificates exist."""
        cert_dir = Path(self.get('SSL_CERT_DIR', '/data/state/certificates'))
        server_name = self.get(f'{self.service_name.upper()}_SERVER_NAME', 'localhost')
        
        cert_file = cert_dir / server_name / 'fullchain.pem'
        key_file = cert_dir / server_name / 'privkey.pem'
        
        return cert_file.exists() and key_file.exists()
    
    def get_ssl_cert_path(self) -> Optional[str]:
        """Get SSL certificate file path."""
        if not self.ssl_cert_exists():
            return None
        
        cert_dir = Path(self.get('SSL_CERT_DIR', '/data/state/certificates'))
        server_name = self.get(f'{self.service_name.upper()}_SERVER_NAME', 'localhost')
        
        return str(cert_dir / server_name / 'fullchain.pem')
    
    def get_ssl_key_path(self) -> Optional[str]:
        """Get SSL private key file path."""
        if not self.ssl_cert_exists():
            return None
        
        cert_dir = Path(self.get('SSL_CERT_DIR', '/data/state/certificates'))
        server_name = self.get(f'{self.service_name.upper()}_SERVER_NAME', 'localhost')
        
        return str(cert_dir / server_name / 'privkey.pem')
    
    def get_ssl_chain_path(self) -> Optional[str]:
        """Get SSL certificate chain file path."""
        if not self.ssl_cert_exists():
            return None
        
        cert_dir = Path(self.get('SSL_CERT_DIR', '/data/state/certificates'))
        server_name = self.get(f'{self.service_name.upper()}_SERVER_NAME', 'localhost')
        
        chain_file = cert_dir / server_name / 'chain.pem'
        return str(chain_file) if chain_file.exists() else None
    
    def format_dns_forwarders(self, forwarders_string: str) -> str:
        """Format DNS forwarders for BIND configuration.
        
        Args:
            forwarders_string: Semicolon-separated list of DNS servers
            
        Returns:
            Formatted forwarders for BIND config
        """
        forwarders = [f.strip() for f in forwarders_string.split(';') if f.strip()]
        return '; '.join([f"{fw};" for fw in forwarders])
    
    def escape_dollar_for_bind(self, value: str) -> str:
        """Escape dollar signs for BIND zone files.
        
        Args:
            value: String that might contain _DOLLAR_ placeholders
            
        Returns:
            String with _DOLLAR_ replaced by $
        """
        return value.replace('_DOLLAR_', '$')
    
    def validate_required_vars(self, required_vars: list) -> bool:
        """Validate that required configuration variables are set.
        
        Args:
            required_vars: List of required variable names
            
        Returns:
            True if all required variables are set
        """
        missing_vars = []
        
        for var in required_vars:
            if not self.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.logger.error(f"Missing required configuration variables: {missing_vars}")
            return False
        
        return True