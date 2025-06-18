"""Health check framework for PodServe services."""

import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Callable, Dict, Any
import json
import logging
from pathlib import Path


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints."""
    
    # Class variable to store health checker reference
    health_checker = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for health checks."""
        if self.path == '/health':
            self.handle_health_check()
        elif self.path == '/ready':
            self.handle_readiness_check()
        elif self.path == '/status':
            self.handle_status_check()
        else:
            self.send_error(404, "Not Found")
    
    def handle_health_check(self):
        """Handle liveness probe - basic service health."""
        try:
            is_healthy = self.health_checker.is_healthy()
            
            if is_healthy:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"status": "healthy", "service": self.health_checker.service_name}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(503)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"status": "unhealthy", "service": self.health_checker.service_name}
                self.wfile.write(json.dumps(response).encode())
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def handle_readiness_check(self):
        """Handle readiness probe - service ready to accept traffic."""
        try:
            is_ready = self.health_checker.is_ready()
            
            if is_ready:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"status": "ready", "service": self.health_checker.service_name}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(503)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"status": "not_ready", "service": self.health_checker.service_name}
                self.wfile.write(json.dumps(response).encode())
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def handle_status_check(self):
        """Handle detailed status check."""
        try:
            status = self.health_checker.get_detailed_status()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "error", "error": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr."""
        self.health_checker.logger.debug(f"Health check request: {format % args}")


class HealthChecker:
    """Health check manager for services."""
    
    def __init__(self, service_name: str, config_manager):
        """Initialize health checker.
        
        Args:
            service_name: Name of the service
            config_manager: Configuration manager instance
        """
        self.service_name = service_name
        self.config = config_manager
        self.logger = logging.getLogger(f"{service_name}.health")
        
        # Health check configuration
        self.health_port = int(self.config.get('HEALTH_CHECK_PORT', '8080'))
        self.health_interval = int(self.config.get('HEALTH_CHECK_INTERVAL', '30'))
        
        # Health check state
        self.health_checks = {}
        self.last_health_check = None
        self.health_status = False
        self.ready_status = False
        
        # HTTP server for health endpoints
        self.http_server = None
        self.server_thread = None
        self.running = False
        
        # Register default health checks
        self.register_default_checks()
    
    def register_default_checks(self):
        """Register default health checks for all services."""
        # Check if log directory is writable
        self.register_check('log_directory', self.check_log_directory)
        
        # Check if config directory exists
        self.register_check('config_directory', self.check_config_directory)
        
        # Service-specific checks will be added by subclasses
    
    def register_check(self, name: str, check_function: Callable[[], bool]):
        """Register a health check function.
        
        Args:
            name: Name of the health check
            check_function: Function that returns True if healthy
        """
        self.health_checks[name] = check_function
        self.logger.debug(f"Registered health check: {name}")
    
    def check_log_directory(self) -> bool:
        """Check if log directory is accessible and writable."""
        try:
            log_dir = Path(self.config.get('LOGS_DIR', '/data/logs'))
            if not log_dir.exists():
                return False
            
            # Try to write a test file
            test_file = log_dir / f".health_check_{self.service_name}"
            test_file.write_text("health check")
            test_file.unlink()
            
            return True
        except Exception:
            return False
    
    def check_config_directory(self) -> bool:
        """Check if config directory exists."""
        try:
            config_dir = Path(self.config.get('CONFIG_DIR', '/data/config'))
            return config_dir.exists()
        except Exception:
            return False
    
    def is_healthy(self) -> bool:
        """Check if service is healthy (liveness probe).
        
        Returns:
            True if service is healthy
        """
        try:
            # Run all health checks
            failed_checks = []
            
            for name, check_func in self.health_checks.items():
                try:
                    if not check_func():
                        failed_checks.append(name)
                except Exception as e:
                    self.logger.warning(f"Health check {name} failed with exception: {e}")
                    failed_checks.append(name)
            
            # Update health status
            self.health_status = len(failed_checks) == 0
            self.last_health_check = time.time()
            
            if failed_checks:
                self.logger.warning(f"Failed health checks: {failed_checks}")
            
            return self.health_status
            
        except Exception as e:
            self.logger.error(f"Error during health check: {e}")
            return False
    
    def is_ready(self) -> bool:
        """Check if service is ready to accept traffic (readiness probe).
        
        Returns:
            True if service is ready
        """
        # Default implementation - same as health check
        # Override in service-specific implementations
        return self.is_healthy()
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status information.
        
        Returns:
            Dictionary with detailed status information
        """
        status = {
            "service": self.service_name,
            "timestamp": time.time(),
            "healthy": self.health_status,
            "ready": self.ready_status,
            "last_check": self.last_health_check,
            "checks": {}
        }
        
        # Run individual checks and collect results
        for name, check_func in self.health_checks.items():
            try:
                result = check_func()
                status["checks"][name] = {
                    "status": "pass" if result else "fail",
                    "healthy": result
                }
            except Exception as e:
                status["checks"][name] = {
                    "status": "error",
                    "healthy": False,
                    "error": str(e)
                }
        
        # Add service-specific status
        service_status = self.get_service_status()
        if service_status:
            status.update(service_status)
        
        return status
    
    def get_service_status(self) -> Optional[Dict[str, Any]]:
        """Get service-specific status information.
        
        Override in service implementations to provide additional status.
        
        Returns:
            Dictionary with service-specific status or None
        """
        return None
    
    def start(self):
        """Start the health check HTTP server."""
        if self.running:
            return
        
        try:
            # Set the health checker reference in the handler class
            HealthCheckHandler.health_checker = self
            
            self.http_server = HTTPServer(('0.0.0.0', self.health_port), HealthCheckHandler)
            
            # Start server in background thread
            self.server_thread = threading.Thread(
                target=self.http_server.serve_forever,
                daemon=True
            )
            self.server_thread.start()
            
            self.running = True
            self.logger.info(f"Health check server started on port {self.health_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start health check server: {e}")
            raise
    
    def stop(self):
        """Stop the health check HTTP server."""
        if not self.running:
            return
        
        try:
            if self.http_server:
                self.http_server.shutdown()
                self.http_server.server_close()
                
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            self.running = False
            self.logger.info("Health check server stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping health check server: {e}")


class ServiceHealthChecker(HealthChecker):
    """Extended health checker with service-specific checks."""
    
    def __init__(self, service_name: str, config_manager, service_instance):
        """Initialize service health checker.
        
        Args:
            service_name: Name of the service
            config_manager: Configuration manager instance
            service_instance: Instance of the service being checked
        """
        super().__init__(service_name, config_manager)
        self.service = service_instance
        
        # Register service-specific health check
        self.register_check('service_health', self.check_service_health)
    
    def check_service_health(self) -> bool:
        """Check service-specific health."""
        try:
            if hasattr(self.service, 'health_check'):
                return self.service.health_check()
            return True
        except Exception:
            return False
    
    def is_ready(self) -> bool:
        """Check if service is ready."""
        # Service is ready if it's healthy and has completed initialization
        if not self.is_healthy():
            return False
        
        # Check if service has been running for minimum time
        if hasattr(self.service, 'start_time'):
            min_ready_time = int(self.config.get('MIN_READY_TIME', '5'))
            if time.time() - self.service.start_time < min_ready_time:
                return False
        
        self.ready_status = True
        return True
    
    def get_service_status(self) -> Optional[Dict[str, Any]]:
        """Get service-specific status."""
        status = {}
        
        # Add service runtime information
        if hasattr(self.service, 'start_time'):
            status['uptime'] = time.time() - self.service.start_time
        
        if hasattr(self.service, 'processes'):
            status['background_processes'] = len(self.service.processes)
        
        # Add configuration information
        status['configuration'] = {
            'ssl_enabled': self.config.is_ssl_enabled(),
            'ssl_cert_exists': self.config.ssl_cert_exists(),
        }
        
        return status