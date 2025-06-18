"""Pytest configuration and fixtures."""

import socket
import time
from typing import Generator

import pytest


def wait_for_port(host: str, port: int, timeout: int = 30) -> bool:
    """Wait for a port to be available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (socket.error, ConnectionRefusedError):
            time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def container_services() -> Generator[dict, None, None]:
    """Fixture to ensure container services are running."""
    services = {
        "http": {"host": "localhost", "port": 80},
        "https": {"host": "localhost", "port": 443},
        "smtp": {"host": "localhost", "port": 25},
        "imap": {"host": "localhost", "port": 143},
        "imaps": {"host": "localhost", "port": 993},
    }

    # Check if services are available
    available_services = {}
    for name, config in services.items():
        if wait_for_port(config["host"], config["port"], timeout=10):
            available_services[name] = config
        else:
            pytest.skip(
                f"Service {name} not available on " f"{config['host']}:{config['port']}"
            )

    yield available_services


@pytest.fixture
def web_service(container_services: dict) -> dict:
    """HTTP/HTTPS web service fixture."""
    if "http" not in container_services:
        pytest.skip("HTTP service not available")
    return container_services["http"]


@pytest.fixture
def mail_service(container_services: dict) -> dict:
    """Mail service fixture."""
    if "smtp" not in container_services:
        pytest.skip("Mail service not available")
    return {
        "smtp": container_services.get("smtp"),
        "imap": container_services.get("imap"),
        "imaps": container_services.get("imaps"),
    }
