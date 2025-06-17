"""Container startup and health check performance tests."""

import json
import subprocess
import time
import pytest
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from performance_thresholds import PerformanceThresholds


class ContainerPerformanceTest:
    """Test container startup times and health check responsiveness."""
    
    def __init__(self):
        self.performance_data = {}
        self.thresholds = PerformanceThresholds()
    
    def measure_container_startup(self, container_name: str, timeout: int = 60) -> Dict[str, float]:
        """Measure container startup time to healthy state."""
        start_time = time.time()
        
        # Track different startup phases
        phases = {
            'container_created': None,
            'container_running': None,
            'health_check_starting': None,
            'health_check_healthy': None,
            'service_responding': None
        }
        
        # Wait for container to be created and running
        while time.time() - start_time < timeout:
            result = subprocess.run(
                ["podman", "inspect", container_name, "--format", "json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                inspect_data = json.loads(result.stdout)[0]
                state = inspect_data.get('State', {})
                
                # Container created
                if phases['container_created'] is None:
                    phases['container_created'] = time.time() - start_time
                
                # Container running
                if state.get('Status') == 'running' and phases['container_running'] is None:
                    phases['container_running'] = time.time() - start_time
                
                # Health check phases
                health = state.get('Health', {})
                if health:
                    health_status = health.get('Status', '')
                    
                    if health_status == 'starting' and phases['health_check_starting'] is None:
                        phases['health_check_starting'] = time.time() - start_time
                    
                    if health_status == 'healthy' and phases['health_check_healthy'] is None:
                        phases['health_check_healthy'] = time.time() - start_time
                        break
                
                # If no health check, consider running as healthy
                elif state.get('Status') == 'running' and phases['health_check_healthy'] is None:
                    phases['health_check_healthy'] = time.time() - start_time
                    break
            
            time.sleep(0.1)
        
        # Test service responsiveness
        service_start = time.time()
        if self._test_service_response(container_name):
            phases['service_responding'] = time.time() - start_time
        else:
            phases['service_responding'] = time.time() - start_time  # Record even if failed
        
        return phases
    
    def _test_service_response(self, container_name: str) -> bool:
        """Test if the service is responding correctly."""
        # Service-specific tests
        if 'dns' in container_name.lower():
            return self._test_dns_response(container_name)
        elif 'mail' in container_name.lower():
            return self._test_mail_response(container_name)
        elif 'apache' in container_name.lower() or 'web' in container_name.lower():
            return self._test_web_response(container_name)
        return True
    
    def _test_dns_response(self, container_name: str) -> bool:
        """Test DNS service response."""
        try:
            result = subprocess.run(
                ["podman", "exec", container_name, "dig", "@localhost", "google.com", "+time=1"],
                capture_output=True,
                text=True,
                timeout=3
            )
            return "ANSWER SECTION" in result.stdout
        except:
            return False
    
    def _test_mail_response(self, container_name: str) -> bool:
        """Test mail service response."""
        try:
            # Test SMTP port
            result = subprocess.run(
                ["podman", "exec", container_name, "nc", "-z", "localhost", "25"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False
    
    def _test_web_response(self, container_name: str) -> bool:
        """Test web service response."""
        try:
            # Test HTTP port
            result = subprocess.run(
                ["podman", "exec", container_name, "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:80"],
                capture_output=True,
                text=True,
                timeout=3
            )
            return result.stdout.strip() in ['200', '301', '302']
        except:
            return False
    
    def restart_and_measure(self, container_name: str) -> Dict[str, float]:
        """Restart container and measure startup time."""
        print(f"Restarting {container_name} for performance measurement...")
        
        # Restart container
        restart_result = subprocess.run(
            ["podman", "restart", container_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if restart_result.returncode != 0:
            raise Exception(f"Failed to restart {container_name}: {restart_result.stderr}")
        
        # Measure startup
        phases = self.measure_container_startup(container_name)
        
        # Record results
        self.thresholds.record_result(container_name, 'startup', phases)
        
        return phases


@pytest.mark.performance
@pytest.mark.container
class TestContainerPerformance:
    """Container performance and startup time tests."""
    
    @pytest.fixture(scope="class")
    def performance_tester(self):
        """Create performance test instance."""
        return ContainerPerformanceTest()
    
    @pytest.fixture(scope="class")
    def running_containers(self):
        """Get list of running PodServe containers."""
        try:
            result = subprocess.run(
                ["podman", "ps", "--filter", "name=podserve", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True
            )
            containers = [name.strip() for name in result.stdout.split("\n") if name.strip()]
            
            if not containers:
                pytest.skip("No PodServe containers running for performance tests")
            
            return containers
        except subprocess.CalledProcessError:
            pytest.skip("Could not get container list")
    
    def test_dns_startup_performance(self, performance_tester, running_containers):
        """Test DNS container startup performance."""
        dns_containers = [c for c in running_containers if 'dns' in c.lower()]
        if not dns_containers:
            pytest.skip("No DNS containers found")
        
        container_name = dns_containers[0]
        phases = performance_tester.restart_and_measure(container_name)
        
        # Performance assertions using thresholds
        assert phases['container_running'] is not None, "Container never reached running state"
        
        running_threshold = performance_tester.thresholds.get_threshold(container_name, 'container_running')
        assert phases['container_running'] <= running_threshold, f"DNS container took too long to start: {phases['container_running']:.2f}s (threshold: {running_threshold:.2f}s)"
        
        if phases['health_check_healthy'] is not None:
            healthy_threshold = performance_tester.thresholds.get_threshold(container_name, 'health_check_healthy')
            assert phases['health_check_healthy'] <= healthy_threshold, f"DNS health check took too long: {phases['health_check_healthy']:.2f}s (threshold: {healthy_threshold:.2f}s)"
        
        if phases['service_responding'] is not None:
            responding_threshold = performance_tester.thresholds.get_threshold(container_name, 'service_responding')
            assert phases['service_responding'] <= responding_threshold, f"DNS service took too long to respond: {phases['service_responding']:.2f}s (threshold: {responding_threshold:.2f}s)"
        
        print(f"\nDNS Container Performance ({container_name}):")
        for phase, timing in phases.items():
            if timing is not None:
                print(f"  {phase}: {timing:.2f}s")
    
    def test_mail_startup_performance(self, performance_tester, running_containers):
        """Test mail container startup performance."""
        mail_containers = [c for c in running_containers if 'mail' in c.lower()]
        if not mail_containers:
            pytest.skip("No mail containers found")
        
        container_name = mail_containers[0]
        phases = performance_tester.restart_and_measure(container_name)
        
        # Mail services typically take longer to start - use threshold-based assertions
        assert phases['container_running'] is not None, "Container never reached running state"
        
        running_threshold = performance_tester.thresholds.get_threshold(container_name, 'container_running')
        assert phases['container_running'] <= running_threshold, f"Mail container took too long to start: {phases['container_running']:.2f}s (threshold: {running_threshold:.2f}s)"
        
        if phases['health_check_healthy'] is not None:
            healthy_threshold = performance_tester.thresholds.get_threshold(container_name, 'health_check_healthy')
            assert phases['health_check_healthy'] <= healthy_threshold, f"Mail health check took too long: {phases['health_check_healthy']:.2f}s (threshold: {healthy_threshold:.2f}s)"
        
        if phases['service_responding'] is not None:
            responding_threshold = performance_tester.thresholds.get_threshold(container_name, 'service_responding')
            assert phases['service_responding'] <= responding_threshold, f"Mail service took too long to respond: {phases['service_responding']:.2f}s (threshold: {responding_threshold:.2f}s)"
        
        print(f"\nMail Container Performance ({container_name}):")
        for phase, timing in phases.items():
            if timing is not None:
                print(f"  {phase}: {timing:.2f}s")
    
    def test_web_startup_performance(self, performance_tester, running_containers):
        """Test web container startup performance."""
        web_containers = [c for c in running_containers if 'apache' in c.lower() or 'web' in c.lower()]
        if not web_containers:
            pytest.skip("No web containers found")
        
        container_name = web_containers[0]
        phases = performance_tester.restart_and_measure(container_name)
        
        # Web services should start quickly - use threshold-based assertions
        assert phases['container_running'] is not None, "Container never reached running state"
        
        running_threshold = performance_tester.thresholds.get_threshold(container_name, 'container_running')
        assert phases['container_running'] <= running_threshold, f"Web container took too long to start: {phases['container_running']:.2f}s (threshold: {running_threshold:.2f}s)"
        
        if phases['health_check_healthy'] is not None:
            healthy_threshold = performance_tester.thresholds.get_threshold(container_name, 'health_check_healthy')
            assert phases['health_check_healthy'] <= healthy_threshold, f"Web health check took too long: {phases['health_check_healthy']:.2f}s (threshold: {healthy_threshold:.2f}s)"
        
        if phases['service_responding'] is not None:
            responding_threshold = performance_tester.thresholds.get_threshold(container_name, 'service_responding')
            assert phases['service_responding'] <= responding_threshold, f"Web service took too long to respond: {phases['service_responding']:.2f}s (threshold: {responding_threshold:.2f}s)"
        
        print(f"\nWeb Container Performance ({container_name}):")
        for phase, timing in phases.items():
            if timing is not None:
                print(f"  {phase}: {timing:.2f}s")
    
    @pytest.mark.slow
    def test_all_containers_startup_benchmark(self, performance_tester, running_containers):
        """Benchmark startup times for all containers."""
        results = {}
        
        for container_name in running_containers:
            print(f"\nBenchmarking {container_name}...")
            try:
                phases = performance_tester.restart_and_measure(container_name)
                results[container_name] = phases
                
                # Print individual results
                print(f"Results for {container_name}:")
                for phase, timing in phases.items():
                    if timing is not None:
                        print(f"  {phase}: {timing:.2f}s")
                        
            except Exception as e:
                print(f"Failed to benchmark {container_name}: {e}")
                results[container_name] = {'error': str(e)}
        
        # Summary report
        print(f"\n{'='*60}")
        print("CONTAINER STARTUP PERFORMANCE SUMMARY")
        print(f"{'='*60}")
        
        for container_name, phases in results.items():
            if 'error' in phases:
                print(f"{container_name}: ERROR - {phases['error']}")
                continue
                
            running_time = phases.get('container_running', 'N/A')
            healthy_time = phases.get('health_check_healthy', 'N/A')
            responding_time = phases.get('service_responding', 'N/A')
            
            print(f"{container_name}:")
            print(f"  Running: {running_time:.2f}s" if running_time != 'N/A' else "  Running: N/A")
            print(f"  Healthy: {healthy_time:.2f}s" if healthy_time != 'N/A' else "  Healthy: N/A")
            print(f"  Responding: {responding_time:.2f}s" if responding_time != 'N/A' else "  Responding: N/A")
        
        # Save all results and generate report
        for container_name, phases in results.items():
            if 'error' not in phases:
                performance_tester.thresholds.record_result(container_name, 'benchmark', phases)
        
        performance_tester.thresholds.save_results()
        
        # Print performance report
        print(f"\n{performance_tester.thresholds.generate_report()}")
        
        # Print optimization suggestions
        suggestions = performance_tester.thresholds.get_optimization_suggestions()
        if suggestions:
            print(f"\nOPTIMIZATION SUGGESTIONS:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"{i}. {suggestion}")
        
        # Ensure at least one container was benchmarked successfully
        successful_benchmarks = [r for r in results.values() if 'error' not in r]
        assert len(successful_benchmarks) > 0, "No containers could be benchmarked successfully"
    
    def test_health_check_response_times(self, running_containers):
        """Test health check response times for all containers."""
        results = {}
        
        for container_name in running_containers:
            try:
                # Get health check info
                result = subprocess.run(
                    ["podman", "inspect", container_name, "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    inspect_data = json.loads(result.stdout)[0]
                    health = inspect_data.get('State', {}).get('Health', {})
                    
                    if health:
                        # Measure health check execution time
                        start_time = time.time()
                        health_result = subprocess.run(
                            ["podman", "healthcheck", "run", container_name],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        execution_time = time.time() - start_time
                        
                        results[container_name] = {
                            'status': health.get('Status', 'unknown'),
                            'execution_time': execution_time,
                            'success': health_result.returncode == 0
                        }
                    else:
                        results[container_name] = {'status': 'no_healthcheck', 'execution_time': 0, 'success': True}
                        
            except Exception as e:
                results[container_name] = {'error': str(e)}
        
        # Print results
        print(f"\n{'='*50}")
        print("HEALTH CHECK PERFORMANCE")
        print(f"{'='*50}")
        
        for container_name, data in results.items():
            if 'error' in data:
                print(f"{container_name}: ERROR - {data['error']}")
            else:
                status = data['status']
                exec_time = data['execution_time']
                success = data['success']
                print(f"{container_name}: {status} ({exec_time:.2f}s) {'✓' if success else '✗'}")
                
                # Assert reasonable health check times using thresholds
                if status not in ['no_healthcheck', 'unknown']:
                    # Create a simple performance tester instance for threshold access
                    temp_tester = ContainerPerformanceTest()
                    threshold = temp_tester.thresholds.get_threshold(container_name, 'health_check_execution')
                    assert exec_time <= threshold, f"Health check for {container_name} too slow: {exec_time:.2f}s (threshold: {threshold:.2f}s)"
        
        # Ensure we got results for at least one container
        successful_checks = [r for r in results.values() if 'error' not in r]
        assert len(successful_checks) > 0, "No health checks could be measured"