"""Base service class and service runner for PodServe."""

import os
import signal
import sys
import time
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import logging

from podserve.core.config import ConfigManager
from podserve.core.logging import setup_service_logging, capture_subprocess_logs
from podserve.core.health import HealthChecker


class BaseService(ABC):
    """Abstract base class for all PodServe services."""
    
    def __init__(self, service_name: str, debug: bool = False):
        """Initialize the base service.
        
        Args:
            service_name: Name of the service
            debug: Whether to enable debug logging
        """
        self.service_name = service_name
        self.debug = debug
        self.logger = setup_service_logging(service_name, debug)
        self.config = ConfigManager(service_name)
        self.health_checker = HealthChecker(service_name, self.config)
        
        # Service state
        self.running = False
        self.shutdown_requested = False
        self.processes = []  # Track subprocess handles
        
        # Set up signal handlers
        self.setup_signal_handlers()
        
        # Create required directories
        self.create_directories()
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.shutdown_requested = True
            self.stop()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    def create_directories(self):
        """Create required directories for the service."""
        directories = [
            self.config.get('CONFIG_DIR', '/data/config'),
            self.config.get('LOGS_DIR', '/data/logs'),
            self.config.get('STATE_DIR', '/data/state'),
        ]
        
        # Add service-specific directories
        service_dirs = self.get_service_directories()
        directories.extend(service_dirs)
        
        for directory in directories:
            path = Path(directory)
            try:
                path.mkdir(parents=True, exist_ok=True)
                # Set proper ownership if running as root
                if os.getuid() == 0:
                    uid = int(self.config.get('PODSERVE_UID', '1000'))
                    gid = int(self.config.get('PODSERVE_GID', '1000'))
                    os.chown(path, uid, gid)
                
                self.logger.debug(f"Created directory: {directory}")
            except Exception as e:
                self.logger.error(f"Failed to create directory {directory}: {e}")
                raise
    
    @abstractmethod
    def get_service_directories(self) -> List[str]:
        """Get list of service-specific directories to create.
        
        Returns:
            List of directory paths
        """
        pass
    
    @abstractmethod
    def configure(self) -> bool:
        """Configure the service by generating configuration files.
        
        Returns:
            True if configuration was successful
        """
        pass
    
    @abstractmethod
    def start_service(self) -> bool:
        """Start the actual service process.
        
        Returns:
            True if service started successfully
        """
        pass
    
    @abstractmethod
    def stop_service(self) -> bool:
        """Stop the service process.
        
        Returns:
            True if service stopped successfully
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Perform service-specific health check.
        
        Returns:
            True if service is healthy
        """
        pass
    
    def get_service_directories(self) -> List[str]:
        """Get service-specific directories. Override in subclasses."""
        return []
    
    def validate_configuration(self) -> bool:
        """Validate service configuration before starting.
        
        Returns:
            True if configuration is valid
        """
        # Check required variables
        required_vars = self.get_required_config_vars()
        if not self.config.validate_required_vars(required_vars):
            return False
        
        # Perform service-specific validation
        return self.validate_service_config()
    
    @abstractmethod
    def get_required_config_vars(self) -> List[str]:
        """Get list of required configuration variables.
        
        Returns:
            List of required variable names
        """
        pass
    
    def validate_service_config(self) -> bool:
        """Perform service-specific configuration validation.
        
        Returns:
            True if configuration is valid
        """
        return True
    
    def run_subprocess(self, command: List[str], capture_output: bool = True,
                      background: bool = False) -> Union[subprocess.Popen, bool, None]:
        """Run a subprocess with logging.
        
        Args:
            command: Command and arguments to run
            capture_output: Whether to capture and log output
            background: Whether to run in background
            
        Returns:
            Process handle if background=True, None otherwise
        """
        self.logger.info(f"Running command: {' '.join(command)}")
        
        try:
            if background:
                # Start process in background
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE if capture_output else None,
                    stderr=subprocess.PIPE if capture_output else None,
                    text=True
                )
                
                self.processes.append(process)
                
                if capture_output:
                    # Start thread to capture output
                    import threading
                    
                    def log_output():
                        capture_subprocess_logs(self.logger, process, self.service_name)
                    
                    thread = threading.Thread(target=log_output, daemon=True)
                    thread.start()
                
                return process
            
            else:
                # Run synchronously
                if capture_output:
                    process = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    if process.stdout:
                        for line in process.stdout.strip().split('\n'):
                            if line.strip():
                                self.logger.info(f"[CMD] {line}")
                    
                    if process.stderr:
                        for line in process.stderr.strip().split('\n'):
                            if line.strip():
                                self.logger.warning(f"[CMD] {line}")
                    
                    if process.returncode != 0:
                        self.logger.error(f"Command failed with return code {process.returncode}")
                        return False
                    
                    return True
                
                else:
                    process = subprocess.run(command, check=False)
                    if process.returncode != 0:
                        self.logger.error(f"Command failed with return code {process.returncode}")
                        return False
                    
                    return True
                
        except Exception as e:
            self.logger.error(f"Error running command {' '.join(command)}: {e}")
            return False
    
    def start(self) -> bool:
        """Start the service with full lifecycle management.
        
        Returns:
            True if service started successfully
        """
        self.logger.info(f"Starting {self.service_name} service")
        
        try:
            # Validate configuration
            if not self.validate_configuration():
                self.logger.error("Configuration validation failed")
                return False
            
            # Configure the service
            self.logger.info("Configuring service")
            if not self.configure():
                self.logger.error("Service configuration failed")
                return False
            
            # Start health checker
            self.health_checker.start()
            
            # Start the service
            self.logger.info("Starting service process")
            if not self.start_service():
                self.logger.error("Failed to start service process")
                return False
            
            self.running = True
            self.logger.info(f"{self.service_name} service started successfully")
            
            # Enter main service loop
            self.service_loop()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting service: {e}")
            return False
    
    def service_loop(self):
        """Main service loop - keeps service running until shutdown."""
        self.logger.info("Entering service loop")
        
        try:
            while self.running and not self.shutdown_requested:
                # Perform periodic health checks
                if not self.health_check():
                    self.logger.warning("Health check failed")
                
                # Check if any background processes have died
                for process in self.processes[:]:  # Copy list to avoid modification during iteration
                    if process.poll() is not None:
                        self.logger.warning(f"Background process {process.pid} exited with code {process.returncode}")
                        self.processes.remove(process)
                
                # Sleep briefly
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
            self.shutdown_requested = True
        
        finally:
            self.stop()
    
    def stop(self) -> bool:
        """Stop the service gracefully.
        
        Returns:
            True if service stopped successfully
        """
        if not self.running:
            return True
        
        self.logger.info(f"Stopping {self.service_name} service")
        self.running = False
        
        try:
            # Stop health checker
            self.health_checker.stop()
            
            # Stop service-specific processes
            if not self.stop_service():
                self.logger.warning("Service-specific stop failed")
            
            # Terminate any remaining background processes
            for process in self.processes:
                if process.poll() is None:  # Still running
                    self.logger.info(f"Terminating background process {process.pid}")
                    process.terminate()
                    
                    # Wait for graceful termination
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"Force killing process {process.pid}")
                        process.kill()
                        process.wait()
            
            self.processes.clear()
            self.logger.info(f"{self.service_name} service stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping service: {e}")
            return False
    
    def reload(self) -> bool:
        """Reload service configuration.
        
        Returns:
            True if reload was successful
        """
        self.logger.info("Reloading service configuration")
        
        try:
            # Reload configuration
            self.config.load_environment_variables()
            
            # Reconfigure
            if not self.configure():
                self.logger.error("Configuration reload failed")
                return False
            
            self.logger.info("Service configuration reloaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Error reloading configuration: {e}")
            return False
    
    def run(self) -> bool:
        """Run the service (default implementation calls start).
        
        Returns:
            True if service completed successfully
        """
        return self.start()


class ServiceRunner:
    """Runs PodServe services."""
    
    def __init__(self):
        """Initialize service runner."""
        self.logger = logging.getLogger('podserve.runner')
    
    def run_service(self, service_name: str, debug: bool = False):
        """Run a specific service.
        
        Args:
            service_name: Name of the service to run
            debug: Whether to enable debug logging
        """
        try:
            # Import and instantiate the service
            if service_name == 'mail':
                from podserve.services.mail import MailService
                service = MailService(debug=debug)
            elif service_name == 'apache':
                from podserve.services.apache import ApacheService
                service = ApacheService(debug=debug)
            elif service_name == 'dns':
                from podserve.services.dns import DNSService
                service = DNSService(debug=debug)
            elif service_name == 'certbot':
                from podserve.services.certbot import CertbotService
                service = CertbotService(debug=debug)
            elif service_name == 'certificates':
                from podserve.services.certificates import CertificateService
                service = CertificateService(debug=debug)
            elif service_name == 'dns':
                from podserve.services.dns import DNSService
                service = DNSService(debug=debug)
            else:
                raise ValueError(f"Unknown service: {service_name}")
            
            # Start the service
            if not service.start():
                sys.exit(1)
            
        except Exception as e:
            print(f"Error running service {service_name}: {e}", file=sys.stderr)
            sys.exit(1)