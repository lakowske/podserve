"""Certificate management service for PodServe-Harmony.

This service handles SSL/TLS certificate generation, renewal, and distribution
for all PodServe services requiring TLS encryption.

Supports:
- Self-signed certificates (development)
- Let's Encrypt certificates (production)
- Automatic renewal
- Multiple certificate methods
"""

import os
import sys
import time
import subprocess
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from podserve.core.service import BaseService


class CertificateService(BaseService):
    """Certificate management service supporting multiple certificate methods."""
    
    def __init__(self, debug: bool = False):
        """Initialize the certificate service.
        
        Args:
            debug: Whether to enable debug logging
        """
        # Set up directory paths before calling super().__init__()
        # since super().__init__() calls create_directories() which needs these
        self.cert_dir = Path("/data/state/certificates")
        self.config_dir = Path("/data/config/certificates")
        
        super().__init__("certificates", debug)
        
        # Configuration
        self.domain = self.config.get("DOMAIN", "lab.sethlakowske.com")
        self.email = self.config.get("CERTBOT_EMAIL", f"admin@{self.domain}")
        self.method = self.config.get("CERTBOT_METHOD", "self-signed")
        self.staging = self.config.get("CERTBOT_STAGING", "false").lower() == "true"
        
        self.logger.info(f"Certificate service initialized for domain: {self.domain}")
        self.logger.info(f"Certificate method: {self.method}")
        
    def configure(self) -> bool:
        """Configure the certificate service.
        
        Returns:
            True if configuration successful, False otherwise
        """
        try:
            self.logger.info("Configuring certificate service")
            
            # Create certificate directories
            self.cert_dir.mkdir(parents=True, exist_ok=True)
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Set proper permissions for certificate access
            # Certificates should be readable by services but keys protected
            os.chmod(str(self.cert_dir), 0o755)
            os.chmod(str(self.config_dir), 0o755)
            
            self.logger.info("Certificate directories created and configured")
            return True
            
        except Exception as e:
            self.logger.error(f"Certificate service configuration failed: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def start_processes(self) -> bool:
        """Start certificate management processes.
        
        Returns:
            True if processes started successfully, False otherwise
        """
        try:
            self.logger.info("Starting certificate management")
            
            # Initialize certificates if they don't exist
            if not self._certificates_exist():
                self.logger.info("No certificates found, generating initial certificates")
                if not self.init_certificates():
                    return False
            else:
                self.logger.info("Existing certificates found")
                
            # Validate existing certificates
            if not self._validate_certificates():
                self.logger.warning("Certificate validation failed, regenerating")
                if not self.init_certificates():
                    return False
                    
            self.logger.info("Certificate management started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start certificate processes: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def run_mode(self, mode: str) -> bool:
        """Run the service in a specific mode.
        
        Args:
            mode: Operating mode ('init', 'renew', 'cron', 'check')
            
        Returns:
            True if mode executed successfully, False otherwise
        """
        modes = {
            "init": self.init_certificates,
            "renew": self.renew_certificates,
            "cron": self.run_cron_mode,
            "check": self.check_certificates
        }
        
        if mode not in modes:
            self.logger.error(f"Unknown mode: {mode}")
            return False
            
        self.logger.info(f"Running certificate service in mode: {mode}")
        return modes[mode]()
    
    def init_certificates(self) -> bool:
        """Initialize certificates based on configured method.
        
        Returns:
            True if certificates created successfully, False otherwise
        """
        try:
            self.logger.info(f"Initializing certificates using method: {self.method}")
            
            if self.method == "self-signed":
                return self._create_self_signed()
            elif self.method == "standalone":
                return self._certbot_standalone()
            elif self.method.startswith("dns-"):
                return self._certbot_dns(self.method)
            else:
                self.logger.error(f"Unknown certificate method: {self.method}")
                return False
                
        except Exception as e:
            self.logger.error(f"Certificate initialization failed: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def _create_self_signed(self) -> bool:
        """Create self-signed certificates for development.
        
        Returns:
            True if certificates created successfully, False otherwise
        """
        try:
            self.logger.info("Generating self-signed certificate")
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Certificate subject
            subject = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, self.domain),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PodServe Development"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Self-Signed"),
            ])
            
            # Build certificate
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                subject  # Self-signed, so issuer == subject
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(self.domain),
                    x509.DNSName(f"*.{self.domain}"),
                    x509.DNSName("localhost"),
                ]),
                critical=False,
            ).add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            ).add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            ).sign(private_key, hashes.SHA256())
            
            # Save certificate files
            return self._save_certificate_files(cert, private_key)
            
        except Exception as e:
            self.logger.error(f"Self-signed certificate generation failed: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def _save_certificate_files(self, cert: x509.Certificate, private_key) -> bool:
        """Save certificate and private key files.
        
        Args:
            cert: The certificate to save
            private_key: The private key to save
            
        Returns:
            True if files saved successfully, False otherwise
        """
        try:
            # Serialize certificate
            cert_pem = cert.public_bytes(serialization.Encoding.PEM)
            
            # Serialize private key
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Write certificate file (readable by services)
            cert_file = self.cert_dir / "cert.pem"
            with open(cert_file, 'wb') as f:
                f.write(cert_pem)
            os.chmod(str(cert_file), 0o644)
            
            # Write private key file (readable by services but more restricted)
            key_file = self.cert_dir / "privkey.pem"
            with open(key_file, 'wb') as f:
                f.write(key_pem)
            os.chmod(str(key_file), 0o640)
            
            # Create fullchain.pem (same as cert.pem for self-signed)
            fullchain_file = self.cert_dir / "fullchain.pem"
            with open(fullchain_file, 'wb') as f:
                f.write(cert_pem)
            os.chmod(str(fullchain_file), 0o644)
            
            self.logger.info(f"Certificate files saved to {self.cert_dir}")
            self.logger.debug(f"Certificate: {cert_file}")
            self.logger.debug(f"Private key: {key_file}")
            self.logger.debug(f"Full chain: {fullchain_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save certificate files: {e}")
            return False
    
    def _certbot_standalone(self) -> bool:
        """Use certbot standalone mode for Let's Encrypt certificates.
        
        Returns:
            True if certificates obtained successfully, False otherwise
        """
        try:
            self.logger.info("Requesting Let's Encrypt certificate via standalone mode")
            
            cmd = [
                "certbot", "certonly",
                "--standalone",
                "--non-interactive",
                "--agree-tos",
                "--email", self.email,
                "--domains", self.domain,
                "--cert-path", str(self.cert_dir)
            ]
            
            if self.staging:
                cmd.append("--staging")
                self.logger.info("Using Let's Encrypt staging environment")
                
            result = self.run_subprocess(cmd)
            
            if result:
                # Copy certbot certificates to our standard location
                return self._copy_certbot_certificates()
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Certbot standalone failed: {e}")
            return False
    
    def _certbot_dns(self, provider: str) -> bool:
        """Use certbot DNS challenge for Let's Encrypt certificates.
        
        Args:
            provider: DNS provider (e.g., 'dns-cloudflare')
            
        Returns:
            True if certificates obtained successfully, False otherwise
        """
        try:
            self.logger.info(f"Requesting Let's Encrypt certificate via {provider}")
            
            # Load provider credentials
            provider_name = provider.replace('dns-', '')
            creds_file = self.config_dir / f"{provider_name}.ini"
            
            if not creds_file.exists():
                self.logger.error(f"Credentials file not found: {creds_file}")
                return False
                
            cmd = [
                "certbot", "certonly",
                f"--{provider}",
                f"--{provider}-credentials", str(creds_file),
                "--non-interactive",
                "--agree-tos",
                "--email", self.email,
                "--domains", self.domain
            ]
            
            if self.staging:
                cmd.append("--staging")
                
            result = self.run_subprocess(cmd)
            
            if result:
                return self._copy_certbot_certificates()
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Certbot DNS challenge failed: {e}")
            return False
    
    def _copy_certbot_certificates(self) -> bool:
        """Copy certbot certificates to our standard location.
        
        Returns:
            True if certificates copied successfully, False otherwise
        """
        try:
            # Certbot typically puts certificates in /etc/letsencrypt/live/{domain}/
            certbot_dir = Path(f"/etc/letsencrypt/live/{self.domain}")
            
            if not certbot_dir.exists():
                self.logger.error(f"Certbot certificates not found at {certbot_dir}")
                return False
            
            # Copy certificate files
            files_to_copy = [
                ("cert.pem", "cert.pem"),
                ("privkey.pem", "privkey.pem"),
                ("fullchain.pem", "fullchain.pem"),
            ]
            
            for src_name, dst_name in files_to_copy:
                src_file = certbot_dir / src_name
                dst_file = self.cert_dir / dst_name
                
                if not src_file.exists():
                    self.logger.error(f"Source file not found: {src_file}")
                    return False
                
                # Copy file
                import shutil
                shutil.copy2(str(src_file), str(dst_file))
                
                # Set appropriate permissions
                if dst_name == "privkey.pem":
                    os.chmod(str(dst_file), 0o640)
                else:
                    os.chmod(str(dst_file), 0o644)
            
            self.logger.info("Certbot certificates copied successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to copy certbot certificates: {e}")
            return False
    
    def renew_certificates(self) -> bool:
        """Check and renew certificates if needed.
        
        Returns:
            True if renewal check completed successfully, False otherwise
        """
        try:
            self.logger.info("Checking certificates for renewal")
            
            if self._needs_renewal():
                self.logger.info("Certificates need renewal, regenerating")
                return self.init_certificates()
            else:
                self.logger.info("Certificates are still valid")
                return True
                
        except Exception as e:
            self.logger.error(f"Certificate renewal check failed: {e}")
            return False
    
    def _needs_renewal(self, days: int = 30) -> bool:
        """Check if certificates need renewal.
        
        Args:
            days: Number of days before expiration to trigger renewal
            
        Returns:
            True if certificates need renewal, False otherwise
        """
        try:
            cert_file = self.cert_dir / "cert.pem"
            
            if not cert_file.exists():
                self.logger.warning("Certificate file not found, renewal needed")
                return True
            
            # Load and check certificate
            with open(cert_file, 'rb') as f:
                cert_data = f.read()
                
            cert = x509.load_pem_x509_certificate(cert_data)
            expires = cert.not_valid_after
            days_left = (expires - datetime.utcnow()).days
            
            self.logger.debug(f"Certificate expires in {days_left} days")
            
            return days_left < days
            
        except Exception as e:
            self.logger.error(f"Failed to check certificate expiration: {e}")
            return True  # Assume renewal needed if we can't check
    
    def run_cron_mode(self) -> bool:
        """Run in cron mode with automatic renewal.
        
        Returns:
            True if cron mode started successfully, False otherwise
        """
        try:
            self.logger.info("Starting certificate service in cron mode")
            
            # Initial certificate setup
            if not self.configure() or not self.start_processes():
                return False
            
            # Schedule daily renewal checks at 2 AM
            schedule.every().day.at("02:00").do(self._renewal_job)
            
            self.logger.info("Certificate renewal scheduled for daily 2 AM checks")
            
            # Run scheduler loop
            while not self.shutdown_requested:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            self.logger.info("Certificate cron mode stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Certificate cron mode failed: {e}")
            return False
    
    def _renewal_job(self):
        """Scheduled renewal job."""
        try:
            self.logger.info("Running scheduled certificate renewal check")
            self.renew_certificates()
        except Exception as e:
            self.logger.error(f"Scheduled renewal failed: {e}")
    
    def check_certificates(self) -> bool:
        """Check and display certificate status.
        
        Returns:
            True if check completed successfully, False otherwise
        """
        try:
            self.logger.info("Checking certificate status")
            
            cert_file = self.cert_dir / "cert.pem"
            
            if not cert_file.exists():
                self.logger.warning("No certificate file found")
                return False
            
            # Load certificate
            with open(cert_file, 'rb') as f:
                cert_data = f.read()
                
            cert = x509.load_pem_x509_certificate(cert_data)
            
            # Display certificate information
            subject = cert.subject.rfc4514_string()
            issuer = cert.issuer.rfc4514_string()
            not_before = cert.not_valid_before
            not_after = cert.not_valid_after
            days_left = (not_after - datetime.utcnow()).days
            
            self.logger.info(f"Certificate subject: {subject}")
            self.logger.info(f"Certificate issuer: {issuer}")
            self.logger.info(f"Valid from: {not_before}")
            self.logger.info(f"Valid until: {not_after}")
            self.logger.info(f"Days remaining: {days_left}")
            
            # Check if renewal needed
            if self._needs_renewal():
                self.logger.warning("Certificate renewal recommended")
            else:
                self.logger.info("Certificate is valid and up to date")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Certificate check failed: {e}")
            return False
    
    def _certificates_exist(self) -> bool:
        """Check if certificate files exist.
        
        Returns:
            True if all required certificate files exist, False otherwise
        """
        required_files = ["cert.pem", "privkey.pem", "fullchain.pem"]
        
        for filename in required_files:
            file_path = self.cert_dir / filename
            if not file_path.exists():
                return False
                
        return True
    
    def _validate_certificates(self) -> bool:
        """Validate existing certificates.
        
        Returns:
            True if certificates are valid, False otherwise
        """
        try:
            cert_file = self.cert_dir / "cert.pem"
            
            if not cert_file.exists():
                return False
            
            # Load and validate certificate
            with open(cert_file, 'rb') as f:
                cert_data = f.read()
                
            cert = x509.load_pem_x509_certificate(cert_data)
            
            # Check if certificate is still valid
            now = datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                self.logger.warning("Certificate is expired or not yet valid")
                return False
                
            # Check if certificate is for the correct domain
            try:
                san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                dns_names = [name.value for name in san_ext.value if isinstance(name, x509.DNSName)]
                
                if self.domain not in dns_names:
                    self.logger.warning(f"Certificate does not include domain {self.domain}")
                    return False
                    
            except x509.ExtensionNotFound:
                # Check common name instead
                cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                if not cn or cn[0].value != self.domain:
                    self.logger.warning(f"Certificate common name does not match domain {self.domain}")
                    return False
            
            self.logger.debug("Certificate validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Certificate validation failed: {e}")
            return False
    
    def get_service_directories(self) -> List[str]:
        """Get service-specific directories to create."""
        return [
            str(self.cert_dir),
            str(self.config_dir)
        ]
    
    def get_required_config_vars(self) -> List[str]:
        """Get required configuration variables."""
        return [
            "DOMAIN",
            "CERTBOT_EMAIL"
        ]
    
    def configure(self) -> bool:
        """Configure the certificate service."""
        try:
            # Ensure directories exist
            self.cert_dir.mkdir(parents=True, exist_ok=True)
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("Certificate service configuration completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure certificate service: {e}")
            return False
    
    def start_service(self) -> bool:
        """Start the certificate service."""
        try:
            # Initialize certificates if they don't exist
            if not self.init_certificates():
                return False
            
            # Start renewal scheduler if in cron mode
            if hasattr(self, 'mode') and self.mode == 'cron':
                self.start_renewal_scheduler()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start certificate service: {e}")
            return False
    
    def stop_service(self) -> bool:
        """Stop the certificate service."""
        try:
            # Cancel any scheduled renewal jobs
            schedule.clear()
            self.logger.info("Certificate service stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop certificate service: {e}")
            return False

    def health_check(self) -> bool:
        """Perform health check for the certificate service.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Check if certificate files exist and are valid
            if not self._certificates_exist():
                self.logger.error("Health check failed: certificate files missing")
                return False
                
            if not self._validate_certificates():
                self.logger.error("Health check failed: certificate validation failed")
                return False
                
            # Check if certificates will expire soon
            if self._needs_renewal(days=7):  # Warning if expires within 7 days
                self.logger.warning("Health check warning: certificates expire soon")
                # Don't fail health check, just warn
                
            self.logger.debug("Certificate service health check passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False