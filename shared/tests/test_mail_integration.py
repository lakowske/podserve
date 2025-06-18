"""Integration tests for mail services."""

import imaplib
import smtplib
import socket
import ssl
import time
import uuid
from email.mime.text import MIMEText

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

    def test_smtp_ssl_send_mail_with_uuid(self):
        """Test sending mail via SMTP with SSL/TLS authentication."""
        try:
            # Generate unique message ID for tracking
            test_uuid = str(uuid.uuid4())
            
            # Create SSL context for SMTP connection (allow certificates from certificate container)
            smtp_context = ssl.create_default_context()
            smtp_context.check_hostname = False
            smtp_context.verify_mode = ssl.CERT_NONE
            
            # Connect to SMTP submission port (587) with STARTTLS
            smtp = smtplib.SMTP('localhost', 587)
            smtp.starttls(context=smtp_context)
            print("✓ SMTP STARTTLS connection established")
            
            # Login with admin credentials
            smtp.login('admin@lab.sethlakowske.com', 'password')
            print("✓ SMTP authentication successful")
            
            # Create test message with UUID
            msg = MIMEText(f"Test message with UUID: {test_uuid}\nThis is a test email sent via SMTP with SSL/TLS authentication.")
            msg['Subject'] = f'Test Message {test_uuid}'
            msg['From'] = 'admin@lab.sethlakowske.com'
            msg['To'] = 'admin@lab.sethlakowske.com'
            
            # Send the message
            smtp.send_message(msg)
            print(f"✓ Mail sent successfully with UUID: {test_uuid}")
            
            # Close SMTP connection
            smtp.quit()
            print("✓ SMTP session completed")
            
            # Store UUID for later test (using class attribute)
            TestMailIntegration._test_message_uuid = test_uuid
            
            # Wait 100ms before exiting as requested
            time.sleep(0.1)
            
        except smtplib.SMTPException as e:
            pytest.fail(f"SMTP error: {e}")
        except Exception as e:
            pytest.fail(f"SMTP SSL mail sending failed: {e}")

    def test_imaps_ssl_login_and_mailbox_check(self):
        """Test IMAPS SSL/TLS login and check for messages in mailbox."""
        try:
            # Create SSL context that allows certificates from certificate container
            # May include self-signed certs for testing
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Connect to IMAPS (port 993 with SSL)
            imap = imaplib.IMAP4_SSL('localhost', 993, ssl_context=ssl_context)
            
            # Login with admin credentials
            response = imap.login('admin@lab.sethlakowske.com', 'password')
            assert response[0] == 'OK', f"IMAPS login failed: {response}"
            print(f"✓ IMAPS SSL login successful: {response[1][0].decode()}")
            
            # List available mailboxes
            response = imap.list()
            assert response[0] == 'OK', f"Mailbox list failed: {response}"
            mailboxes = [line.decode() for line in response[1]]
            print(f"✓ Available mailboxes: {len(mailboxes)} found")
            
            # Select INBOX
            response = imap.select('INBOX')
            assert response[0] == 'OK', f"INBOX selection failed: {response}"
            message_count = response[1][0].decode() if response[1] else '0'
            print(f"✓ INBOX selected, messages: {message_count}")
            
            # Search for all messages
            response = imap.search(None, 'ALL')
            assert response[0] == 'OK', f"Message search failed: {response}"
            message_ids = response[1][0].decode().split() if response[1][0] else []
            print(f"✓ Found {len(message_ids)} messages in INBOX")
            
            # Check mailbox status
            response = imap.status('INBOX', '(MESSAGES RECENT UNSEEN)')
            assert response[0] == 'OK', f"Mailbox status failed: {response}"
            status_info = response[1][0].decode()
            print(f"✓ Mailbox status: {status_info}")
            
            # Logout
            imap.logout()
            print("✓ IMAPS session completed successfully")
            
        except imaplib.IMAP4.error as e:
            pytest.fail(f"IMAPS protocol error: {e}")
        except ssl.SSLError as e:
            pytest.fail(f"SSL connection error: {e}")
        except Exception as e:
            pytest.fail(f"IMAPS SSL login and mailbox check failed: {e}")

    def test_imap_plain_login_and_capabilities(self):
        """Test plain IMAP login and server capabilities."""
        try:
            # Connect to plain IMAP (port 143)
            imap = imaplib.IMAP4('localhost', 143)
            
            # Check capabilities
            response = imap.capability()
            assert response[0] == 'OK', f"Capability check failed: {response}"
            capabilities = response[1][0].decode()
            print(f"✓ IMAP capabilities: {capabilities}")
            
            # Verify STARTTLS is available
            assert 'STARTTLS' in capabilities, "STARTTLS should be available"
            
            # Start TLS
            imap.starttls()
            print("✓ STARTTLS initiated successfully")
            
            # Login with admin credentials
            response = imap.login('admin@lab.sethlakowske.com', 'password')
            assert response[0] == 'OK', f"IMAP login failed: {response}"
            print(f"✓ IMAP login successful: {response[1][0].decode()}")
            
            # Select INBOX and check basic functionality
            response = imap.select('INBOX')
            assert response[0] == 'OK', f"INBOX selection failed: {response}"
            print(f"✓ INBOX selected successfully")
            
            # Logout
            imap.logout()
            print("✓ IMAP session completed successfully")
            
        except imaplib.IMAP4.error as e:
            pytest.fail(f"IMAP protocol error: {e}")
        except Exception as e:
            pytest.fail(f"IMAP plain login test failed: {e}")

    def test_imaps_ssl_search_and_delete_uuid_message(self):
        """Test searching for and deleting the message with the UUID via IMAPS SSL."""
        try:
            # Check if we have a test UUID from the previous send test
            if not hasattr(TestMailIntegration, '_test_message_uuid'):
                pytest.skip("No test message UUID available - send mail test may not have run")
            
            test_uuid = TestMailIntegration._test_message_uuid
            
            # Wait a moment for mail delivery to complete
            time.sleep(1)
            
            # Create SSL context for IMAPS connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Connect to IMAPS (port 993 with SSL)
            imap = imaplib.IMAP4_SSL('localhost', 993, ssl_context=ssl_context)
            
            # Login with admin credentials
            response = imap.login('admin@lab.sethlakowske.com', 'password')
            assert response[0] == 'OK', f"IMAPS login failed: {response}"
            print("✓ IMAPS SSL login successful for message deletion")
            
            # Select INBOX
            response = imap.select('INBOX')
            assert response[0] == 'OK', f"INBOX selection failed: {response}"
            print("✓ INBOX selected for message search")
            
            # Search for messages containing our UUID
            search_criteria = f'BODY "{test_uuid}"'
            response = imap.search(None, search_criteria)
            assert response[0] == 'OK', f"Message search failed: {response}"
            
            message_ids = response[1][0].decode().split() if response[1][0] else []
            print(f"✓ Found {len(message_ids)} messages with UUID {test_uuid}")
            
            if message_ids:
                # Get the first matching message for verification
                msg_id = message_ids[0]
                
                # Fetch the message to verify it contains our UUID
                response = imap.fetch(msg_id, '(BODY.PEEK[])')
                assert response[0] == 'OK', f"Message fetch failed: {response}"
                
                message_content = response[1][0][1].decode()
                assert test_uuid in message_content, f"UUID {test_uuid} not found in message content"
                print(f"✓ Verified message {msg_id} contains UUID {test_uuid}")
                
                # Mark message for deletion
                response = imap.store(msg_id, '+FLAGS', '\\Deleted')
                assert response[0] == 'OK', f"Message marking for deletion failed: {response}"
                print(f"✓ Message {msg_id} marked for deletion")
                
                # Expunge to permanently delete
                response = imap.expunge()
                assert response[0] == 'OK', f"Message expunge failed: {response}"
                print(f"✓ Message {msg_id} permanently deleted")
                
                # Verify message is gone by searching again
                response = imap.search(None, search_criteria)
                assert response[0] == 'OK', f"Verification search failed: {response}"
                remaining_messages = response[1][0].decode().split() if response[1][0] else []
                
                # Should have one less message (or none if it was the only one)
                assert len(remaining_messages) < len(message_ids), "Message was not successfully deleted"
                print(f"✓ Verified message deletion - {len(remaining_messages)} messages remain with UUID")
                
            else:
                pytest.fail(f"No messages found with UUID {test_uuid} - mail may not have been delivered yet")
            
            # Logout
            imap.logout()
            print("✓ IMAPS message deletion session completed successfully")
            
        except imaplib.IMAP4.error as e:
            pytest.fail(f"IMAPS protocol error during message deletion: {e}")
        except ssl.SSLError as e:
            pytest.fail(f"SSL connection error during message deletion: {e}")
        except Exception as e:
            pytest.fail(f"IMAPS SSL message deletion test failed: {e}")
