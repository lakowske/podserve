"""Dual logging system for PodServe services."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class DualLogger:
    """Logger that outputs to both stdout/stderr and log files."""
    
    def __init__(self, service_name: str, log_level: str = "INFO"):
        """Initialize dual logger for a service.
        
        Args:
            service_name: Name of the service (used for log file naming)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.service_name = service_name
        self.log_level = getattr(logging, log_level.upper())
        self.logger = logging.getLogger(service_name)
        self.setup_logging()
    
    def setup_logging(self):
        """Set up dual logging handlers."""
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Set log level
        self.logger.setLevel(self.log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler (stdout/stderr)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(self.log_level)
        
        # Error handler for stderr
        error_handler = logging.StreamHandler(sys.stderr)
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.WARNING)  # Only warnings and errors to stderr
        
        # File handler (for Claude inspection)
        log_dir = Path("/data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{self.service_name}.log"
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(self.log_level)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(file_handler)
        
        # Prevent duplicate logs from root logger
        self.logger.propagate = False
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger
    
    def log_subprocess_output(self, process_output: str, level: str = "INFO"):
        """Log subprocess output with appropriate level.
        
        Args:
            process_output: Output from subprocess
            level: Log level for the output
        """
        log_level = getattr(logging, level.upper())
        
        # Split output into lines and log each
        for line in process_output.strip().split('\n'):
            if line.strip():  # Skip empty lines
                self.logger.log(log_level, f"[SUBPROCESS] {line}")


def setup_service_logging(service_name: str, debug: bool = False) -> logging.Logger:
    """Set up logging for a service with dual output.
    
    Args:
        service_name: Name of the service
        debug: Whether to enable debug logging
        
    Returns:
        Configured logger instance
    """
    # Determine log level from environment or debug flag
    log_level = os.environ.get('LOG_LEVEL', 'DEBUG' if debug else 'INFO')
    
    # Create dual logger
    dual_logger = DualLogger(service_name, log_level)
    
    # Log startup information
    logger = dual_logger.get_logger()
    logger.info(f"Starting {service_name} service")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Logging to console and /data/logs/{service_name}.log")
    
    return logger


def capture_subprocess_logs(logger: logging.Logger, process, service_name: str):
    """Capture and log subprocess output in real-time.
    
    Args:
        logger: Logger instance to use
        process: Subprocess object
        service_name: Name of the service for log prefixing
    """
    import select
    import subprocess
    
    # Create file objects for stdout and stderr
    stdout_fd = process.stdout.fileno() if process.stdout else None
    stderr_fd = process.stderr.fileno() if process.stderr else None
    
    # Monitor both stdout and stderr
    while process.poll() is None:
        # Use select to check for available data
        ready_fds = []
        if stdout_fd:
            ready_fds.append(stdout_fd)
        if stderr_fd:
            ready_fds.append(stderr_fd)
        
        if ready_fds:
            readable, _, _ = select.select(ready_fds, [], [], 0.1)
            
            for fd in readable:
                if fd == stdout_fd:
                    line = process.stdout.readline()
                    if line:
                        logger.info(f"[{service_name}] {line.strip()}")
                elif fd == stderr_fd:
                    line = process.stderr.readline()
                    if line:
                        logger.warning(f"[{service_name}] {line.strip()}")
    
    # Capture any remaining output
    if process.stdout:
        remaining_stdout = process.stdout.read()
        if remaining_stdout:
            for line in remaining_stdout.strip().split('\n'):
                if line.strip():
                    logger.info(f"[{service_name}] {line}")
    
    if process.stderr:
        remaining_stderr = process.stderr.read()
        if remaining_stderr:
            for line in remaining_stderr.strip().split('\n'):
                if line.strip():
                    logger.warning(f"[{service_name}] {line}")