"""Common utilities for PodServe services."""

import os
import pwd
import grp
import stat
import socket
import subprocess
import ssl
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging


def ensure_directory(path: str, owner: Optional[str] = None, 
                    mode: Optional[int] = None) -> bool:
    """Ensure directory exists with proper permissions.
    
    Args:
        path: Directory path to create
        owner: Username to own the directory
        mode: Octal mode for directory permissions
        
    Returns:
        True if directory exists or was created successfully
    """
    logger = logging.getLogger('podserve.utils')
    
    try:
        path_obj = Path(path)
        
        # Create directory if it doesn't exist
        path_obj.mkdir(parents=True, exist_ok=True)
        
        # Set ownership if specified
        if owner and os.getuid() == 0:  # Only if running as root
            try:
                user_info = pwd.getpwnam(owner)
                os.chown(path, user_info.pw_uid, user_info.pw_gid)
                logger.debug(f"Set ownership of {path} to {owner}")
            except KeyError:
                logger.warning(f"User {owner} not found, skipping ownership change")
        
        # Set permissions if specified
        if mode is not None:
            os.chmod(path, mode)
            logger.debug(f"Set permissions of {path} to {oct(mode)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to ensure directory {path}: {e}")
        return False


def copy_file_with_permissions(src: str, dest: str, owner: Optional[str] = None,
                              mode: Optional[int] = None) -> bool:
    """Copy file and set proper permissions.
    
    Args:
        src: Source file path
        dest: Destination file path
        owner: Username to own the file
        mode: Octal mode for file permissions
        
    Returns:
        True if file was copied successfully
    """
    logger = logging.getLogger('podserve.utils')
    
    try:
        src_path = Path(src)
        dest_path = Path(dest)
        
        if not src_path.exists():
            logger.error(f"Source file does not exist: {src}")
            return False
        
        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        dest_path.write_bytes(src_path.read_bytes())
        logger.debug(f"Copied {src} to {dest}")
        
        # Set ownership if specified
        if owner and os.getuid() == 0:
            try:
                user_info = pwd.getpwnam(owner)
                os.chown(dest, user_info.pw_uid, user_info.pw_gid)
                logger.debug(f"Set ownership of {dest} to {owner}")
            except KeyError:
                logger.warning(f"User {owner} not found, skipping ownership change")
        
        # Set permissions if specified
        if mode is not None:
            os.chmod(dest, mode)
            logger.debug(f"Set permissions of {dest} to {oct(mode)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy file {src} to {dest}: {e}")
        return False


def check_port_available(port: int, host: str = '0.0.0.0') -> bool:
    """Check if a port is available for binding.
    
    Args:
        port: Port number to check
        host: Host address to check
        
    Returns:
        True if port is available
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = sock.bind((host, port))
            return True
    except OSError:
        return False


def check_service_listening(port: int, host: str = 'localhost',
                           timeout: int = 5) -> bool:
    """Check if a service is listening on a specific port.
    
    Args:
        port: Port number to check
        host: Host address to check
        timeout: Connection timeout in seconds
        
    Returns:
        True if service is listening
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def validate_ssl_certificate(cert_path: str, key_path: str) -> bool:
    """Validate SSL certificate and key files.
    
    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file
        
    Returns:
        True if certificate and key are valid
    """
    logger = logging.getLogger('podserve.utils')
    
    try:
        cert_file = Path(cert_path)
        key_file = Path(key_path)
        
        if not cert_file.exists():
            logger.error(f"Certificate file not found: {cert_path}")
            return False
        
        if not key_file.exists():
            logger.error(f"Key file not found: {key_path}")
            return False
        
        # Try to load the certificate and key
        context = ssl.create_default_context()
        context.load_cert_chain(cert_path, key_path)
        
        logger.debug(f"SSL certificate validation successful: {cert_path}")
        return True
        
    except Exception as e:
        logger.error(f"SSL certificate validation failed: {e}")
        return False


def get_ssl_certificate_info(cert_path: str) -> Optional[Dict[str, Any]]:
    """Get information about an SSL certificate.
    
    Args:
        cert_path: Path to certificate file
        
    Returns:
        Dictionary with certificate information or None
    """
    logger = logging.getLogger('podserve.utils')
    
    try:
        # Use openssl to get certificate info
        result = subprocess.run([
            'openssl', 'x509', '-in', cert_path, '-text', '-noout'
        ], capture_output=True, text=True, check=True)
        
        # Parse basic info (simplified)
        info = {'valid': True, 'path': cert_path}
        
        # Get expiration date
        exp_result = subprocess.run([
            'openssl', 'x509', '-in', cert_path, '-enddate', '-noout'
        ], capture_output=True, text=True, check=True)
        
        if exp_result.stdout:
            info['expires'] = exp_result.stdout.strip().replace('notAfter=', '')
        
        # Get subject
        subj_result = subprocess.run([
            'openssl', 'x509', '-in', cert_path, '-subject', '-noout'
        ], capture_output=True, text=True, check=True)
        
        if subj_result.stdout:
            info['subject'] = subj_result.stdout.strip().replace('subject=', '')
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get certificate info for {cert_path}: {e}")
        return None


def run_command_with_retry(command: List[str], retries: int = 3,
                          delay: float = 1.0) -> bool:
    """Run a command with retry logic.
    
    Args:
        command: Command and arguments to run
        retries: Number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        True if command succeeded
    """
    logger = logging.getLogger('podserve.utils')
    
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            if attempt > 0:
                logger.info(f"Command succeeded on attempt {attempt + 1}")
            return True
            
        except subprocess.CalledProcessError as e:
            if attempt < retries:
                logger.warning(f"Command failed (attempt {attempt + 1}/{retries + 1}): {e}")
                if delay > 0:
                    import time
                    time.sleep(delay)
            else:
                logger.error(f"Command failed after {retries + 1} attempts: {e}")
                if e.stderr:
                    logger.error(f"Command stderr: {e.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Unexpected error running command: {e}")
            return False
    
    return False


def is_process_running(pid: int) -> bool:
    """Check if a process is running.
    
    Args:
        pid: Process ID to check
        
    Returns:
        True if process is running
    """
    try:
        os.kill(pid, 0)  # Send signal 0 (no-op) to check if process exists
        return True
    except OSError:
        return False


def get_process_by_name(name: str) -> List[int]:
    """Get PIDs of processes with given name.
    
    Args:
        name: Process name to search for
        
    Returns:
        List of PIDs
    """
    try:
        result = subprocess.run(['pgrep', '-f', name], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            return [int(pid) for pid in result.stdout.strip().split('\n') if pid]
        return []
    except Exception:
        return []


def terminate_process_gracefully(pid: int, timeout: int = 10) -> bool:
    """Terminate a process gracefully with SIGTERM, then SIGKILL if needed.
    
    Args:
        pid: Process ID to terminate
        timeout: Timeout in seconds before using SIGKILL
        
    Returns:
        True if process was terminated
    """
    logger = logging.getLogger('podserve.utils')
    
    try:
        if not is_process_running(pid):
            return True
        
        # Send SIGTERM
        os.kill(pid, 15)  # SIGTERM
        logger.debug(f"Sent SIGTERM to process {pid}")
        
        # Wait for graceful termination
        import time
        for _ in range(timeout):
            if not is_process_running(pid):
                logger.debug(f"Process {pid} terminated gracefully")
                return True
            time.sleep(1)
        
        # Force kill if still running
        if is_process_running(pid):
            os.kill(pid, 9)  # SIGKILL
            logger.warning(f"Force killed process {pid}")
            time.sleep(1)
            return not is_process_running(pid)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to terminate process {pid}: {e}")
        return False


def ensure_user_exists(username: str, uid: Optional[int] = None,
                      gid: Optional[int] = None, home_dir: Optional[str] = None,
                      shell: str = '/bin/false') -> bool:
    """Ensure a system user exists.
    
    Args:
        username: Username to create
        uid: User ID (optional)
        gid: Group ID (optional)
        home_dir: Home directory (optional)
        shell: User shell
        
    Returns:
        True if user exists or was created
    """
    logger = logging.getLogger('podserve.utils')
    
    try:
        # Check if user already exists
        pwd.getpwnam(username)
        logger.debug(f"User {username} already exists")
        return True
        
    except KeyError:
        # User doesn't exist, create it
        pass
    
    try:
        # Create group first if gid is specified
        if gid is not None:
            try:
                # Check if group exists
                grp.getgrgid(gid)
                logger.debug(f"Group {gid} already exists")
            except KeyError:
                # Create group
                group_cmd = ['groupadd', '--system', '--gid', str(gid), f"{username}"]
                result = subprocess.run(group_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create group {gid}: {result.stderr}")
                    # Use default group instead
                    gid = None
        
        # Build useradd command
        cmd = ['useradd', '--system']
        
        if uid is not None:
            cmd.extend(['--uid', str(uid)])
        
        if gid is not None:
            cmd.extend(['--gid', str(gid)])
        
        if home_dir:
            cmd.extend(['--home-dir', home_dir])
            cmd.append('--create-home')
        else:
            cmd.append('--no-create-home')
        
        cmd.extend(['--shell', shell])
        cmd.append(username)
        
        # Create user
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Created system user: {username}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create user {username}: {e}")
        if e.stderr:
            logger.error(f"useradd stderr: {e.stderr}")
        return False
    
    except Exception as e:
        logger.error(f"Unexpected error creating user {username}: {e}")
        return False


def parse_environment_list(env_var: str, separator: str = ';') -> List[str]:
    """Parse environment variable containing separated list.
    
    Args:
        env_var: Environment variable value
        separator: List separator character
        
    Returns:
        List of parsed values
    """
    if not env_var:
        return []
    
    return [item.strip() for item in env_var.split(separator) if item.strip()]


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_disk_usage(path: str) -> Dict[str, int]:
    """Get disk usage statistics for a path.
    
    Args:
        path: Path to check
        
    Returns:
        Dictionary with total, used, and free space in bytes
    """
    try:
        stat_result = os.statvfs(path)
        
        total = stat_result.f_frsize * stat_result.f_blocks
        free = stat_result.f_frsize * stat_result.f_bavail
        used = total - free
        
        return {
            'total': total,
            'used': used,
            'free': free,
            'percent_used': (used / total * 100) if total > 0 else 0
        }
        
    except Exception:
        return {'total': 0, 'used': 0, 'free': 0, 'percent_used': 0}