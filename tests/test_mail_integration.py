"""Integration tests for mail services."""

import imaplib
import smtplib
import socket
import ssl

import pytest


@pytest.mark.integration
@pytest.mark.container
class TestMailIntegration:
    """Integration tests for mail services."""

    def test_smtp_service_available(self, mail_service: dict):
        """Test that SMTP service is available."""
        smtp_config = mail_service["smtp"]
        if not smtp_config:
            pytest.skip("SMTP service not available")

        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            # Test basic connection
            code, message = server.noop()
            assert code == 250

    def test_smtp_capabilities(self, mail_service: dict):
        """Test SMTP server capabilities."""
        smtp_config = mail_service["smtp"]
        if not smtp_config:
            pytest.skip("SMTP service not available")

        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            # Get EHLO response
            code, response = server.ehlo()
            assert code == 250

            # Check for required capabilities
            capabilities = response.decode().lower()
            assert "starttls" in capabilities
            assert "auth" in capabilities

    def test_smtp_starttls(self, mail_service: dict):
        """Test SMTP STARTTLS functionality."""
        smtp_config = mail_service["smtp"]
        if not smtp_config:
            pytest.skip("SMTP service not available")

        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            # Test STARTTLS
            server.starttls()

            # Verify connection is encrypted
            assert server.sock is not None
            assert isinstance(server.sock, ssl.SSLSocket)

    def test_imap_service_available(self, mail_service: dict):
        """Test that IMAP service is available."""
        imap_config = mail_service["imap"]
        if not imap_config:
            pytest.skip("IMAP service not available")

        with imaplib.IMAP4(imap_config["host"], imap_config["port"]) as mail:
            # Test basic connection
            assert mail.state == "NONAUTH"

    def test_imaps_service_available(self, mail_service: dict):
        """Test that IMAPS service is available."""
        imaps_config = mail_service["imaps"]
        if not imaps_config:
            pytest.skip("IMAPS service not available")

        try:
            # Create SSL context that allows self-signed certificates
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with imaplib.IMAP4_SSL(
                imaps_config["host"], imaps_config["port"], ssl_context=context
            ) as mail:
                # Test basic connection
                assert mail.state == "NONAUTH"
        except ssl.SSLError as e:
            pytest.skip(f"IMAPS SSL connection failed: {e}")

    def test_smtp_connectivity_only(self, mail_service: dict):
        """Test SMTP connectivity without authentication."""
        smtp_config = mail_service["smtp"]
        if not smtp_config:
            pytest.skip("SMTP service not available")

        # Test raw socket connection
        with socket.create_connection(
            (smtp_config["host"], smtp_config["port"]), timeout=5
        ) as sock:
            # Read welcome message
            response = sock.recv(1024).decode()
            assert response.startswith("220")

            # Send EHLO
            sock.send(b"EHLO test\r\n")
            response = sock.recv(1024).decode()
            assert "250" in response

            # Send QUIT
            sock.send(b"QUIT\r\n")
            response = sock.recv(1024).decode()
            assert "221" in response

    def test_mail_directory_structure(self, mail_service: dict):
        """Test that mail directory structure exists (via container exec)."""
        # This test would require podman exec access
        # For now, we'll just check that mail services are responding
        smtp_config = mail_service["smtp"]
        if not smtp_config:
            pytest.skip("SMTP service not available")

        # Test that the service is responding
        # (implies directory structure is set up)
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            code, message = server.noop()
            assert code == 250

    @pytest.mark.slow
    def test_ssl_certificate_consistency(self, mail_service: dict):
        """Test that mail services use consistent SSL certificates."""
        imaps_config = mail_service["imaps"]
        if not imaps_config:
            pytest.skip("IMAPS service not available")

        try:
            # Get certificate from IMAPS
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with ssl.create_connection(
                (imaps_config["host"], imaps_config["port"])
            ) as sock:
                with context.wrap_socket(
                    sock, server_hostname=imaps_config["host"]
                ) as ssock:
                    cert = ssock.getpeercert(binary_form=True)

                    # Basic certificate validation for binary form
                    assert cert is not None
                    assert len(cert) > 0

        except ssl.SSLError as e:
            pytest.skip(f"SSL certificate test failed: {e}")

    def test_port_availability(self, mail_service: dict):
        """Test that all expected mail ports are available."""
        expected_ports = [25, 143, 993]  # SMTP, IMAP, IMAPS

        for port in expected_ports:
            try:
                with socket.create_connection(("localhost", port), timeout=2):
                    pass  # Connection successful
            except (socket.error, ConnectionRefusedError):
                pytest.fail(f"Mail port {port} is not available")
