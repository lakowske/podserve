"""Mail service implementation for PodServe."""

import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from podserve.core.service import BaseService
from podserve.core.utils import (
    ensure_directory, copy_file_with_permissions, 
    run_command_with_retry, get_process_by_name,
    terminate_process_gracefully
)


class MailService(BaseService):
    """Mail service managing Postfix and Dovecot."""
    
    def __init__(self, debug: bool = False):
        """Initialize mail service."""
        super().__init__('mail', debug)
        self.postfix_process = None
        self.dovecot_process = None
        self.start_time = time.time()
    
    def get_service_directories(self) -> List[str]:
        """Get mail-specific directories to create."""
        return [
            self.config.get('MAIL_DATA_DIR', '/var/mail/vhosts'),
            '/etc/postfix/maps',
            '/etc/dovecot/conf.d',
            '/var/spool/postfix/private',
            '/var/spool/postfix/public',
        ]
    
    def get_required_config_vars(self) -> List[str]:
        """Get required configuration variables for mail service."""
        return [
            'MAIL_SERVER_NAME',
            'MAIL_DOMAIN'
        ]
    
    def validate_service_config(self) -> bool:
        """Validate mail service configuration."""
        # Check if SSL certificates are available if SSL is enabled
        if self.config.is_ssl_enabled():
            if not self.config.ssl_cert_exists():
                self.logger.warning("SSL enabled but certificates not found")
                return False
        
        return True
    
    def configure(self) -> bool:
        """Configure mail service by generating configuration files."""
        self.logger.info("Configuring mail service")
        
        try:
            # Create virtual mail user
            self.create_vmail_user()
            
            # Generate Postfix configuration
            if not self.configure_postfix():
                return False
            
            # Generate Dovecot configuration
            if not self.configure_dovecot():
                return False
            
            # Create virtual domains and mailboxes
            if not self.create_virtual_config():
                return False
            
            self.logger.info("Mail service configuration completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Mail configuration failed: {e}")
            return False
    
    def create_vmail_user(self):
        """Create virtual mail user."""
        from podserve.core.utils import ensure_user_exists
        
        # Create vmail user for virtual mailboxes
        if not ensure_user_exists('vmail', uid=5000, gid=5000, 
                                home_dir='/var/mail/vhosts'):
            self.logger.warning("Failed to create vmail user")
    
    def configure_postfix(self) -> bool:
        """Generate Postfix configuration."""
        self.logger.info("Configuring Postfix")
        
        try:
            # Prepare SSL configuration
            ssl_config = {}
            if self.config.is_ssl_enabled():
                ssl_config['SSL_CERT_FILE'] = self.config.get_ssl_cert_path()
                ssl_config['SSL_KEY_FILE'] = self.config.get_ssl_key_path()
            
            # Add MUA restrictions to config context
            mua_config = {
                'mua_client_restrictions': 'permit_sasl_authenticated,reject',
                'mua_helo_restrictions': 'permit_sasl_authenticated,reject',
                'mua_sender_restrictions': 'permit_sasl_authenticated,reject'
            }
            ssl_config.update(mua_config)
            
            # Render main.cf with MUA restrictions
            self.config.render_template(
                'main.cf',
                '/etc/postfix/main.cf',
                ssl_config
            )
            
            # Copy master.cf from shell-based implementation  
            master_cf_content = self.get_master_cf_template()
            with open('/etc/postfix/master.cf', 'w') as f:
                f.write(master_cf_content)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Postfix configuration failed: {e}")
            return False
    
    def get_master_cf_template(self) -> str:
        """Get Postfix master.cf template content."""
        return """#
# Postfix master process configuration file.
#
# ==========================================================================
# service type  private unpriv  chroot  wakeup  maxproc command + args
#               (yes)   (yes)   (no)    (never) (100)
# ==========================================================================
smtp      inet  n       -       y       -       -       smtpd
submission inet n       -       y       -       -       smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=encrypt
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_tls_auth_only=yes
  -o smtpd_reject_unlisted_recipient=no
  -o smtpd_client_restrictions=$mua_client_restrictions
  -o smtpd_helo_restrictions=$mua_helo_restrictions
  -o smtpd_sender_restrictions=$mua_sender_restrictions
  -o smtpd_recipient_restrictions=
  -o smtpd_relay_restrictions=permit_sasl_authenticated,reject
  -o milter_macro_daemon_name=ORIGINATING
smtps     inet  n       -       y       -       -       smtpd
  -o syslog_name=postfix/smtps
  -o smtpd_tls_wrappermode=yes
  -o smtpd_sasl_auth_enable=yes
  -o smtpd_reject_unlisted_recipient=no
  -o smtpd_client_restrictions=$mua_client_restrictions
  -o smtpd_helo_restrictions=$mua_helo_restrictions
  -o smtpd_sender_restrictions=$mua_sender_restrictions
  -o smtpd_recipient_restrictions=
  -o smtpd_relay_restrictions=permit_sasl_authenticated,reject
  -o milter_macro_daemon_name=ORIGINATING
pickup    unix  n       -       y       60      1       pickup
cleanup   unix  n       -       y       -       0       cleanup
qmgr      unix  n       -       n       300     1       qmgr
tlsmgr    unix  -       -       y       1000?   1       tlsmgr
rewrite   unix  -       -       y       -       -       trivial-rewrite
bounce    unix  -       -       y       -       0       bounce
defer     unix  -       -       y       -       0       bounce
trace     unix  -       -       y       -       0       bounce
verify    unix  -       -       y       -       1       verify
flush     unix  n       -       y       1000?   0       flush
proxymap  unix  -       -       n       -       -       proxymap
proxywrite unix -       -       n       -       1       proxymap
smtp      unix  -       -       y       -       -       smtp
relay     unix  -       -       y       -       -       smtp
showq     unix  n       -       y       -       -       showq
error     unix  -       -       y       -       -       error
retry     unix  -       -       y       -       -       error
discard   unix  -       -       y       -       -       discard
local     unix  -       n       n       -       -       local
virtual   unix  -       n       n       -       -       virtual
lmtp      unix  -       -       y       -       -       lmtp
anvil     unix  -       -       y       -       1       anvil
scache    unix  -       -       y       -       1       scache
postlog   unix-dgram n  -       n       -       1       postlogd
"""
    
    def configure_dovecot(self) -> bool:
        """Generate Dovecot configuration."""
        self.logger.info("Configuring Dovecot")
        
        try:
            # Prepare SSL configuration
            ssl_config = {}
            if self.config.is_ssl_enabled():
                ssl_config['SSL_CERT_FILE'] = self.config.get_ssl_cert_path()
                ssl_config['SSL_KEY_FILE'] = self.config.get_ssl_key_path()
                chain_path = self.config.get_ssl_chain_path()
                if chain_path:
                    ssl_config['SSL_CHAIN_FILE'] = chain_path
            
            # Render main dovecot.conf
            self.config.render_template(
                'dovecot.conf',
                '/etc/dovecot/dovecot.conf',
                ssl_config
            )
            
            # Render SSL configuration if enabled
            if self.config.is_ssl_enabled():
                self.config.render_template(
                    '10-ssl.conf',
                    '/etc/dovecot/conf.d/10-ssl.conf',
                    ssl_config
                )
            
            # Create DH parameters for SSL
            if self.config.is_ssl_enabled():
                self.generate_dh_params()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Dovecot configuration failed: {e}")
            return False
    
    def generate_dh_params(self):
        """Generate DH parameters for Dovecot SSL."""
        dh_file = '/etc/dovecot/dh.pem'
        
        if not Path(dh_file).exists():
            self.logger.info("Generating DH parameters for Dovecot SSL")
            # Use smaller key size for faster generation in containers
            if not run_command_with_retry([
                'openssl', 'dhparam', '-out', dh_file, '2048'
            ], retries=1):
                self.logger.warning("Failed to generate DH parameters")
    
    def create_virtual_config(self) -> bool:
        """Create virtual domains and mailboxes configuration."""
        self.logger.info("Creating virtual mail configuration")
        
        try:
            domain = self.config.get('MAIL_DOMAIN')
            
            # Create virtual domains file
            domains_file = '/etc/postfix/virtual_domains'
            with open(domains_file, 'w') as f:
                f.write(f"{domain}\tOK\n")
            
            # Create virtual mailbox file (example user)
            vmailbox_file = '/etc/postfix/vmailbox'
            with open(vmailbox_file, 'w') as f:
                f.write(f"admin@{domain}\t{domain}/admin/\n")
                f.write(f"test@{domain}\t{domain}/test/\n")
            
            # Create virtual aliases file
            virtual_file = '/etc/postfix/virtual'
            with open(virtual_file, 'w') as f:
                f.write(f"postmaster@{domain}\tadmin@{domain}\n")
                f.write(f"webmaster@{domain}\tadmin@{domain}\n")
            
            # Create Dovecot users file with test passwords
            users_file = '/etc/dovecot/users'
            with open(users_file, 'w') as f:
                # Use SHA512-CRYPT password hash for 'password'
                hash_pw = '$6$rounds=5000$salt$IxDD3jeSOb5eB1CX5LBsqZFVkJdido3OUILO5Ifz5iwMuTS4XMS130MTSuDDl3aCI6WouIL9AjRbLCelDCy.g.'
                f.write(f"admin@{domain}:{hash_pw}\n")
                f.write(f"test@{domain}:{hash_pw}\n")
            
            # Set proper permissions
            os.chmod(users_file, 0o600)
            
            # Hash the files for Postfix
            for file_path in [domains_file, vmailbox_file, virtual_file]:
                run_command_with_retry(['postmap', file_path])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Virtual configuration failed: {e}")
            return False
    
    def start_service(self) -> bool:
        """Start Postfix and Dovecot services."""
        self.logger.info("Starting mail services")
        
        try:
            # Start Postfix
            if not self.start_postfix():
                return False
            
            # Start Dovecot
            if not self.start_dovecot():
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start mail services: {e}")
            return False
    
    def start_postfix(self) -> bool:
        """Start Postfix service."""
        self.logger.info("Starting Postfix")
        
        try:
            # Start Postfix in foreground mode for container
            self.postfix_process = self.run_subprocess([
                'postfix', 'start-fg'
            ], capture_output=True, background=True)
            
            if self.postfix_process:
                self.logger.info(f"Postfix started with PID {self.postfix_process.pid}")
                return True
            else:
                self.logger.error("Failed to start Postfix")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting Postfix: {e}")
            return False
    
    def start_dovecot(self) -> bool:
        """Start Dovecot service."""
        self.logger.info("Starting Dovecot")
        
        try:
            # Start Dovecot in foreground mode for container
            self.dovecot_process = self.run_subprocess([
                'dovecot', '-F'
            ], capture_output=True, background=True)
            
            if self.dovecot_process:
                self.logger.info(f"Dovecot started with PID {self.dovecot_process.pid}")
                return True
            else:
                self.logger.error("Failed to start Dovecot")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting Dovecot: {e}")
            return False
    
    def stop_service(self) -> bool:
        """Stop mail services."""
        self.logger.info("Stopping mail services")
        
        success = True
        
        # Stop Postfix
        if self.postfix_process and self.postfix_process.poll() is None:
            try:
                self.postfix_process.terminate()
                self.postfix_process.wait(timeout=5)
                self.logger.info("Postfix stopped")
            except subprocess.TimeoutExpired:
                self.postfix_process.kill()
                self.logger.warning("Postfix force killed")
            except Exception as e:
                self.logger.error(f"Error stopping Postfix: {e}")
                success = False
        
        # Stop Dovecot
        if self.dovecot_process and self.dovecot_process.poll() is None:
            try:
                self.dovecot_process.terminate()
                self.dovecot_process.wait(timeout=5)
                self.logger.info("Dovecot stopped")
            except subprocess.TimeoutExpired:
                self.dovecot_process.kill()
                self.logger.warning("Dovecot force killed")
            except Exception as e:
                self.logger.error(f"Error stopping Dovecot: {e}")
                success = False
        
        return success
    
    def health_check(self) -> bool:
        """Perform mail service health check."""
        try:
            # Primary health check: verify services are listening on expected ports
            from podserve.core.utils import check_service_listening
            
            # Check SMTP port (essential)
            if not check_service_listening(25):
                self.logger.warning("SMTP port 25 not responding")
                return False
            
            # Check IMAP port (essential)
            if not check_service_listening(143):
                self.logger.warning("IMAP port 143 not responding")
                return False
            
            # Optional: Check if our managed processes are still running
            # But don't fail health check if they're not (services might be externally managed)
            if self.postfix_process and self.postfix_process.poll() is not None:
                self.logger.debug("Managed Postfix process has exited (service may be externally managed)")
            
            if self.dovecot_process and self.dovecot_process.poll() is not None:
                self.logger.debug("Managed Dovecot process has exited (service may be externally managed)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False