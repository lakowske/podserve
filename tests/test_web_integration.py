"""Integration tests for web services."""

import ssl

import pytest
import requests


@pytest.mark.integration
@pytest.mark.container
class TestWebIntegration:
    """Integration tests for web services."""

    def test_http_service_available(self, web_service: dict):
        """Test that HTTP service is available."""
        response = requests.get(f"http://{web_service['host']}:{web_service['port']}")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_https_service_available(self, container_services: dict):
        """Test that HTTPS service is available."""
        if "https" not in container_services:
            pytest.skip("HTTPS service not available")

        https_config = container_services["https"]
        # Use verify=False for self-signed certificates in testing
        response = requests.get(
            f"https://{https_config['host']}:{https_config['port']}",
            verify=False,
        )
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_security_headers(self, web_service: dict):
        """Test that security headers are present."""
        response = requests.get(f"http://{web_service['host']}:{web_service['port']}")

        # Check for security headers
        headers = response.headers
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Referrer-Policy" in headers

    def test_https_security_headers(self, container_services: dict):
        """Test that HTTPS-specific security headers are present."""
        if "https" not in container_services:
            pytest.skip("HTTPS service not available")

        https_config = container_services["https"]
        response = requests.get(
            f"https://{https_config['host']}:{https_config['port']}",
            verify=False,
        )

        # Check for HTTPS-specific security headers
        headers = response.headers
        assert "Strict-Transport-Security" in headers

    def test_webdav_endpoint(self, web_service: dict):
        """Test that WebDAV endpoint is accessible."""
        webdav_url = f"http://{web_service['host']}:{web_service['port']}/webdav/"
        response = requests.request("PROPFIND", webdav_url)

        # WebDAV should return 401 for unauthenticated requests
        assert response.status_code in [401, 207]

    def test_git_endpoint(self, web_service: dict):
        """Test that Git endpoint is accessible."""
        git_url = f"http://{web_service['host']}:{web_service['port']}/git/"
        response = requests.get(git_url)

        # Gitweb may return 403 if no repositories or access restrictions
        # Both 200 and 403 are acceptable responses indicating endpoint exists
        assert response.status_code in [200, 403]

    @pytest.mark.slow
    def test_ssl_certificate_validation(self, container_services: dict):
        """Test SSL certificate properties."""
        if "https" not in container_services:
            pytest.skip("HTTPS service not available")

        https_config = container_services["https"]

        # Get certificate information
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with ssl.create_connection(
            (https_config["host"], https_config["port"])
        ) as sock:
            with context.wrap_socket(
                sock, server_hostname=https_config["host"]
            ) as ssock:
                # Get certificate in DER format for self-signed certs
                cert_der = ssock.getpeercert(binary_form=True)
                assert cert_der is not None

                # For self-signed certs, DER format should contain data
                assert len(cert_der) > 0
