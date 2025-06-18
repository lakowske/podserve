"""Certbot service implementation for PodServe."""

import time
from typing import List
from pathlib import Path

from podserve.core.service import BaseService


class CertbotService(BaseService):
    """Certificate management service."""
    
    def __init__(self, debug: bool = False):
        """Initialize Certbot service."""
        super().__init__('certbot', debug)
        self.start_time = time.time()
    
    def get_service_directories(self) -> List[str]:
        """Get Certbot-specific directories to create."""
        return [
            '/etc/letsencrypt',
            '/var/lib/letsencrypt',
            '/data/state/certificates',
            '/data/state/certbot',
            '/var/www/html/.well-known/acme-challenge',
        ]
    
    def get_required_config_vars(self) -> List[str]:
        """Get required configuration variables."""
        return [
            'CERT_MODE',
            'CERT_DOMAINS',
            'CERT_EMAIL'
        ]
    
    def configure(self) -> bool:
        """Configure certificate service."""
        self.logger.info("Configuring Certbot certificate service")
        
        try:
            # Create necessary directories
            self.create_certificate_directories()
            
            # Configure Certbot settings
            if not self.configure_certbot():
                return False
            
            # Handle certificate generation based on mode
            cert_mode = self.config.get('CERT_MODE', 'self-signed')
            
            if cert_mode == 'self-signed':
                return self.generate_self_signed_certificates()
            elif cert_mode == 'letsencrypt':
                return self.obtain_letsencrypt_certificates()
            elif cert_mode == 'letsencrypt-staging':
                return self.obtain_letsencrypt_certificates(staging=True)
            else:
                self.logger.warning(f"Unknown certificate mode: {cert_mode}")
                return self.generate_self_signed_certificates()
            
        except Exception as e:
            self.logger.error(f"Certificate configuration failed: {e}")
            return False
    
    def create_certificate_directories(self):
        """Create necessary certificate directories."""
        from podserve.core.utils import ensure_directory
        
        directories = [
            '/etc/letsencrypt',
            '/var/lib/letsencrypt', 
            '/data/state/certificates',
            '/data/state/certbot',
            '/var/www/html/.well-known/acme-challenge'
        ]
        
        for directory in directories:
            ensure_directory(directory)
            
    def configure_certbot(self) -> bool:
        """Configure Certbot settings."""
        try:
            # Prepare Certbot configuration context
            config_context = {
                'CERT_EMAIL': self.config.get('CERT_EMAIL', 'admin@localhost'),
                'CERT_DOMAINS': self.config.get('CERT_DOMAINS', 'localhost'),
                'CERT_WEBROOT': '/var/www/html',
            }
            
            # Render Certbot configuration if template exists
            self.config.render_template(
                'certbot.ini',
                '/etc/letsencrypt/cli.ini',
                config_context
            )
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not render Certbot configuration: {e}")
            return True  # Not critical, continue without template
    
    def generate_self_signed_certificates(self) -> bool:
        """Generate self-signed certificates for all configured domains."""
        self.logger.info("Generating self-signed certificates")
        
        try:
            self.logger.info("Starting self-signed certificate generation")
            domains = self.get_domains_list()
            self.logger.info(f"Domains list: {domains}")
            primary_domain = domains[0] if domains else 'localhost'
            self.logger.info(f"Primary domain: {primary_domain}")
            
            cert_dir = f"/data/state/certificates/{primary_domain}"
            self.logger.info(f"Certificate directory: {cert_dir}")
            
            # Create certificate directory
            self.logger.info(f"Creating certificate directory: {cert_dir}")
            if not self.run_subprocess(['mkdir', '-p', cert_dir]):
                self.logger.error(f"Failed to create certificate directory: {cert_dir}")
                return False
            self.logger.info(f"Certificate directory created successfully: {cert_dir}")
            
            # Generate private key
            self.logger.info(f"Generating private key for {primary_domain}")
            
            # Debug directory permissions
            self.logger.info(f"Checking directory permissions for {cert_dir}")
            if not self.run_subprocess(['ls', '-la', cert_dir]):
                self.logger.error(f"Could not check directory permissions for {cert_dir}")
            
            # Check if directory is writable
            self.logger.info(f"Testing write permissions in {cert_dir}")
            test_file = f"{cert_dir}/test_write"
            if not self.run_subprocess(['touch', test_file]):
                self.logger.error(f"Directory {cert_dir} is not writable")
                return False
            else:
                self.logger.info(f"Directory {cert_dir} is writable")
                # Clean up test file
                self.run_subprocess(['rm', '-f', test_file])
            
            # Generate private key with detailed error logging
            privkey_path = f'{cert_dir}/privkey.pem'
            if not self.run_subprocess([
                'openssl', 'genrsa', '-out', privkey_path, '2048'
            ]):
                self.logger.error(f"Failed to generate private key at {privkey_path}")
                return False
            
            # Create certificate configuration for SAN
            config_file = f'{cert_dir}/cert.conf'
            self.create_openssl_config(config_file, domains)
            
            # Generate certificate signing request
            if not self.run_subprocess([
                'openssl', 'req', '-new', '-key', f'{cert_dir}/privkey.pem',
                '-out', f'{cert_dir}/cert.csr', '-config', config_file
            ]):
                return False
            
            # Generate self-signed certificate
            if not self.run_subprocess([
                'openssl', 'x509', '-req', '-in', f'{cert_dir}/cert.csr',
                '-signkey', f'{cert_dir}/privkey.pem', '-out', f'{cert_dir}/fullchain.pem',
                '-days', '365', '-extensions', 'v3_req', '-extfile', config_file
            ]):
                return False
            
            # Copy fullchain as cert for compatibility
            self.run_subprocess([
                'cp', f'{cert_dir}/fullchain.pem', f'{cert_dir}/cert.pem'
            ])
            
            # Create chain file (empty for self-signed)
            self.run_subprocess([
                'touch', f'{cert_dir}/chain.pem'
            ])
            
            # Set proper permissions
            self.run_subprocess(['chmod', '600', f'{cert_dir}/privkey.pem'])
            self.run_subprocess(['chmod', '644', f'{cert_dir}/fullchain.pem'])
            self.run_subprocess(['chmod', '644', f'{cert_dir}/cert.pem'])
            
            # Clean up temporary files
            self.run_subprocess(['rm', '-f', f'{cert_dir}/cert.csr', config_file])
            
            self.logger.info(f"Self-signed certificate generated for domains: {', '.join(domains)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Certificate generation failed: {e}")
            return False
    
    def create_openssl_config(self, config_file: str, domains: List[str]):
        """Create OpenSSL configuration for multi-domain certificates."""
        primary_domain = domains[0]
        
        config_content = f"""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = {primary_domain}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
"""
        
        for i, domain in enumerate(domains, 1):
            config_content += f"DNS.{i} = {domain}\n"
        
        with open(config_file, 'w') as f:
            f.write(config_content)
    
    def get_domains_list(self) -> List[str]:
        """Get list of domains to generate certificates for."""
        self.logger.debug("Getting domains list")
        cert_domains = self.config.get('CERT_DOMAINS', '')
        self.logger.debug(f"CERT_DOMAINS config: {cert_domains}")
        if cert_domains:
            domains = [d.strip() for d in cert_domains.split(',') if d.strip()]
            self.logger.debug(f"Parsed domains from config: {domains}")
        else:
            # Fallback to service-specific domain names
            domains = []
            if self.config.get('APACHE_SERVER_NAME'):
                domains.append(self.config.get('APACHE_SERVER_NAME'))
            if self.config.get('MAIL_SERVER_NAME'):
                domains.append(self.config.get('MAIL_SERVER_NAME'))
            if not domains:
                domains = ['localhost']
            self.logger.debug(f"Using fallback domains: {domains}")
        
        self.logger.debug(f"Final domains list: {domains}")
        return domains
    
    def obtain_letsencrypt_certificates(self, staging: bool = False) -> bool:
        """Obtain Let's Encrypt certificates using Certbot."""
        env_type = "staging" if staging else "production"
        self.logger.info(f"Obtaining Let's Encrypt certificates ({env_type})")
        
        try:
            domains = self.get_domains_list()
            email = self.config.get('CERT_EMAIL', 'admin@localhost')
            
            # Build certbot command
            cmd = [
                'certbot', 'certonly',
                '--webroot',
                '--webroot-path', '/var/www/html',
                '--email', email,
                '--agree-tos',
                '--non-interactive',
                '--expand',
            ]
            
            # Add staging flag if requested
            if staging:
                cmd.append('--staging')
            
            # Add domains
            for domain in domains:
                cmd.extend(['-d', domain])
            
            # Run certbot
            self.logger.info(f"Running: {' '.join(cmd)}")
            if not self.run_subprocess(cmd):
                self.logger.error("Certbot certificate request failed")
                return False
            
            # Copy certificates to standard location
            primary_domain = domains[0]
            if not self.copy_letsencrypt_certificates(primary_domain):
                return False
            
            self.logger.info(f"Let's Encrypt certificates obtained for: {', '.join(domains)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Let's Encrypt certificate request failed: {e}")
            return False
    
    def copy_letsencrypt_certificates(self, domain: str) -> bool:
        """Copy Let's Encrypt certificates to standard location."""
        try:
            src_dir = f'/etc/letsencrypt/live/{domain}'
            dest_dir = f'/data/state/certificates/{domain}'
            
            from podserve.core.utils import ensure_directory
            ensure_directory(dest_dir)
            
            # Copy certificate files
            files_to_copy = {
                'privkey.pem': 'privkey.pem',
                'fullchain.pem': 'fullchain.pem', 
                'cert.pem': 'cert.pem',
                'chain.pem': 'chain.pem'
            }
            
            for src_file, dest_file in files_to_copy.items():
                src_path = f'{src_dir}/{src_file}'
                dest_path = f'{dest_dir}/{dest_file}'
                
                if not self.run_subprocess(['cp', src_path, dest_path]):
                    self.logger.warning(f"Could not copy {src_file}")
                    continue
                    
                # Set proper permissions
                if 'privkey' in dest_file:
                    self.run_subprocess(['chmod', '600', dest_path])
                else:
                    self.run_subprocess(['chmod', '644', dest_path])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to copy certificates: {e}")
            return False
    
    def renew_certificates(self) -> bool:
        """Renew existing Let's Encrypt certificates."""
        self.logger.info("Renewing Let's Encrypt certificates")
        
        try:
            # Run certbot renew
            if not self.run_subprocess(['certbot', 'renew', '--quiet']):
                self.logger.error("Certificate renewal failed")
                return False
            
            # Copy renewed certificates
            domains = self.get_domains_list()
            if domains:
                self.copy_letsencrypt_certificates(domains[0])
            
            self.logger.info("Certificate renewal completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Certificate renewal failed: {e}")
            return False
    
    def start_service(self) -> bool:
        """Start certificate service (runs once then exits)."""
        self.logger.info("Certificate service configuration completed")
        
        # Check if we should run renewal
        if self.config.get('CERT_AUTO_RENEW', 'false').lower() == 'true':
            self.logger.info("Running certificate renewal check")
            self.renew_certificates()
        
        return True
    
    def stop_service(self) -> bool:
        """Stop certificate service."""
        return True
    
    def health_check(self) -> bool:
        """Perform certificate health check."""
        try:
            domains = self.get_domains_list()
            primary_domain = domains[0] if domains else 'localhost'
            
            cert_dir = f'/data/state/certificates/{primary_domain}'
            cert_file = f'{cert_dir}/fullchain.pem'
            
            # Check if certificate exists
            if not Path(cert_file).exists():
                self.logger.warning(f"Certificate file not found: {cert_file}")
                return False
            
            # Check certificate validity (basic check)
            result = self.run_subprocess([
                'openssl', 'x509', '-in', cert_file, '-noout', '-checkend', '86400'
            ], capture_output=True)
            
            if not result:
                self.logger.warning(f"Certificate {cert_file} expires within 24 hours")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Certificate health check failed: {e}")
            return False