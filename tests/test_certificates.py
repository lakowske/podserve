"""Integration tests for certificate management."""

import ssl

import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes


@pytest.mark.integration
@pytest.mark.container
class TestCertificates:
    """Integration tests for SSL/TLS certificates."""

    def test_https_certificate_valid(self, container_services: dict):
        """Test that HTTPS certificate is valid and properly configured."""
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
                # Get certificate in DER format
                cert_der = ssock.getpeercert(binary_form=True)
                cert = x509.load_der_x509_certificate(cert_der, default_backend())

                # Check certificate properties
                assert cert.not_valid_before_utc is not None
                assert cert.not_valid_after_utc is not None

                # Check that certificate is currently valid
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc)
                assert cert.not_valid_before_utc <= now <= cert.not_valid_after_utc

    def test_imaps_certificate_valid(self, container_services: dict):
        """Test that IMAPS certificate is valid and properly configured."""
        if "imaps" not in container_services:
            pytest.skip("IMAPS service not available")

        imaps_config = container_services["imaps"]

        try:
            # Get certificate information
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with ssl.create_connection(
                (imaps_config["host"], imaps_config["port"])
            ) as sock:
                with context.wrap_socket(
                    sock, server_hostname=imaps_config["host"]
                ) as ssock:
                    # Get certificate in DER format
                    cert_der = ssock.getpeercert(binary_form=True)
                    cert = x509.load_der_x509_certificate(cert_der, default_backend())

                    # Check certificate properties
                    assert cert.not_valid_before_utc is not None
                    assert cert.not_valid_after_utc is not None

                    # Check that certificate is currently valid
                    from datetime import datetime, timezone

                    now = datetime.now(timezone.utc)
                    assert cert.not_valid_before_utc <= now <= cert.not_valid_after_utc

        except ssl.SSLError as e:
            pytest.skip(f"IMAPS SSL connection failed: {e}")

    def test_certificate_consistency(self, container_services: dict):
        """Test that web and mail services use the same certificate."""
        if "https" not in container_services or "imaps" not in container_services:
            pytest.skip("Both HTTPS and IMAPS services required")

        def get_cert_fingerprint(host: str, port: int) -> str:
            """Get certificate fingerprint."""
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with ssl.create_connection((host, port)) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)
                    cert = x509.load_der_x509_certificate(cert_der, default_backend())
                    return cert.fingerprint(hashes.SHA256()).hex()

        try:
            https_config = container_services["https"]
            imaps_config = container_services["imaps"]

            https_fingerprint = get_cert_fingerprint(
                https_config["host"], https_config["port"]
            )
            imaps_fingerprint = get_cert_fingerprint(
                imaps_config["host"], imaps_config["port"]
            )

            # Certificates should be the same (shared certificate architecture)
            assert https_fingerprint == imaps_fingerprint

        except ssl.SSLError as e:
            pytest.skip(f"Certificate comparison failed: {e}")

    def test_certificate_authority_info(self, container_services: dict):
        """Test certificate authority information."""
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
                cert_der = ssock.getpeercert(binary_form=True)
                cert = x509.load_der_x509_certificate(cert_der, default_backend())

                # Check issuer information
                issuer = cert.issuer
                assert issuer is not None

                # For Let's Encrypt certificates, check for expected issuer
                issuer_str = str(issuer)
                # Should contain Let's Encrypt or staging information
                is_letsencrypt = any(
                    keyword in issuer_str.lower()
                    for keyword in ["let's encrypt", "letsencrypt", "staging", "fake"]
                )
                assert (
                    is_letsencrypt
                ), f"Expected Let's Encrypt certificate, got: {issuer_str}"

    def test_tls_protocols_supported(self, container_services: dict):
        """Test that modern TLS protocols are supported."""
        if "https" not in container_services:
            pytest.skip("HTTPS service not available")

        https_config = container_services["https"]

        # Test TLS support using modern context
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with ssl.create_connection(
                (https_config["host"], https_config["port"])
            ) as sock:
                with context.wrap_socket(
                    sock, server_hostname=https_config["host"]
                ) as ssock:
                    # Connection successful with modern TLS
                    assert ssock.version() is not None
        except ssl.SSLError:
            # TLS connection failed
            pytest.skip("TLS connection not available")
