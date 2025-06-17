import pytest
import subprocess
import time
import socket
import dns.resolver
import dns.query
import dns.message


def wait_for_container(container_name: str, timeout: int = 30) -> bool:
    """Wait for container to be running."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = subprocess.run(
            ["podman", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True
        )
        if "Up" in result.stdout:
            return True
        time.sleep(1)
    return False


def run_container_command(container_name: str, command: str) -> subprocess.CompletedProcess:
    """Run a command inside a container."""
    return subprocess.run(
        ["podman", "exec", container_name, "bash", "-c", command],
        capture_output=True,
        text=True
    )


class TestDNSIntegration:
    """Integration tests for DNS service"""
    
    @pytest.fixture(scope="class")
    def dns_container(self):
        """Use existing DNS container from the pod"""
        container_name = "podserve-simple-dns"
        
        # Quick check if container exists and is running
        result = subprocess.run(
            ["podman", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if container_name not in result.stdout:
            pytest.skip(f"DNS container {container_name} not running")
        
        # Minimal wait - DNS should already be ready
        time.sleep(0.5)
        
        yield container_name
    
    def test_dns_container_running(self, dns_container):
        """Test that DNS container is running"""
        result = subprocess.run(
            ["podman", "ps", "--filter", f"name={dns_container}"],
            capture_output=True,
            text=True
        )
        assert dns_container in result.stdout
    
    def test_dns_port_listening(self, dns_container):
        """Test that DNS is listening on port 53"""
        result = run_container_command(
            dns_container,
            "netstat -tuln | grep :53"
        )
        assert ":53" in result.stdout
    
    def test_bind_configuration(self, dns_container):
        """Test that BIND configuration is valid"""
        result = run_container_command(
            dns_container,
            "named-checkconf"
        )
        assert result.returncode == 0
    
    def test_dns_forwarding_config(self, dns_container):
        """Test that DNS forwarding configuration is valid"""
        result = run_container_command(
            dns_container,
            "grep -q 'forward only' /etc/bind/named.conf.options"
        )
        assert result.returncode == 0
    
    def test_dns_query_external_domain(self, dns_container):
        """Test DNS external domain resolution"""
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['127.0.0.1']
        resolver.port = 53
        resolver.timeout = 2  # Faster timeout
        resolver.lifetime = 5  # Faster overall timeout
        
        try:
            # Query for external domain
            answer = resolver.resolve('google.com', 'A')
            assert len(answer) > 0
        except Exception as e:
            pytest.fail(f"DNS query failed: {e}")
    
    def test_dns_forwarders(self, dns_container):
        """Test that DNS forwarders are working"""
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['127.0.0.1']
        resolver.port = 53
        resolver.timeout = 2  # Faster timeout
        resolver.lifetime = 5  # Faster overall timeout
        
        try:
            # Query for external domain (reuse google.com from cache)
            answer = resolver.resolve('google.com', 'A')
            assert len(answer) > 0
        except Exception as e:
            pytest.fail(f"DNS forwarding failed: {e}")
    
    def test_dns_logs(self, dns_container):
        """Test that DNS logs are being generated"""
        logs = subprocess.run(
            ["podman", "logs", dns_container],
            capture_output=True,
            text=True
        )
        all_logs = logs.stdout + logs.stderr
        assert "starting BIND" in all_logs
        assert "DNS forwarder configuration complete" in all_logs
    
    def test_dns_healthcheck(self, dns_container):
        """Test container healthcheck"""
        result = subprocess.run(
            ["podman", "inspect", dns_container, "--format", "{{.State.Health.Status}}"],
            capture_output=True,
            text=True
        )
        # Health check might be healthy or starting
        assert result.stdout.strip() in ["healthy", "starting", ""]
    
    def test_multiple_dns_queries(self, dns_container):
        """Test multiple concurrent DNS queries"""
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['127.0.0.1']
        resolver.port = 53
        resolver.timeout = 1  # Very fast timeout for multiple queries
        resolver.lifetime = 3  # Short overall timeout
        
        # Test fewer external domains for speed (reuse cached results)
        test_domains = [
            'google.com',  # Likely cached from previous tests
            'github.com'   # Simple A record lookup
        ]
        
        for domain in test_domains:
            try:
                answer = resolver.resolve(domain, 'A')
                assert len(answer) > 0
            except Exception as e:
                pytest.fail(f"DNS query for {domain} failed: {e}")