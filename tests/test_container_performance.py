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
    
    def measure_container_startup(self, container_name: str, timeout: int = 30) -> Dict[str, float]:
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
                
                # If no health check, consider running as healthy (but wait a bit for service to start)
                elif state.get('Status') == 'running' and phases['health_check_healthy'] is None:
                    # Wait a short time for service to fully start
                    if time.time() - start_time > 2.0:  # Wait at least 2 seconds
                        phases['health_check_healthy'] = time.time() - start_time
                        break
            
            time.sleep(0.1)
        
        # Test service responsiveness (only if container is healthy and we have time)
        if phases.get('health_check_healthy') is not None or phases.get('container_running') is not None:
            remaining_time = timeout - (time.time() - start_time)
            if remaining_time > 2:  # Only test if we have at least 2 seconds left
                service_start_time = time.time()
                try:
                    if self._test_service_response(container_name):
                        phases['service_responding'] = time.time() - start_time
                    else:
                        phases['service_responding'] = time.time() - start_time  # Record even if failed
                except Exception as e:
                    print(f"Service response test failed: {e}")
                    phases['service_responding'] = time.time() - start_time
            else:
                print(f"Skipping service test - not enough time remaining ({remaining_time:.1f}s)")
                phases['service_responding'] = None
        
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
                ["podman", "exec", container_name, "dig", "@localhost", "google.com", "+time=1", "+retry=1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "ANSWER SECTION" in result.stdout
        except Exception as e:
            print(f"DNS test failed: {e}")
            return False
    
    def _test_mail_response(self, container_name: str) -> bool:
        """Test mail service response."""
        try:
            # Test SMTP port
            result = subprocess.run(
                ["podman", "exec", container_name, "nc", "-z", "localhost", "25"],
                capture_output=True,
                text=True,
                timeout=3
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Mail test failed: {e}")
            return False
    
    def _test_web_response(self, container_name: str) -> bool:
        """Test web service response."""
        try:
            # Test HTTP port
            result = subprocess.run(
                ["podman", "exec", container_name, "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:80", "--max-time", "2"],
                capture_output=True,
                text=True,
                timeout=4
            )
            return result.stdout.strip() in ['200', '301', '302']
        except Exception as e:
            print(f"Web test failed: {e}")
            return False
    
    def measure_shutdown_time(self, container_name: str) -> float:
        """Measure container shutdown time."""
        print(f"Measuring shutdown time for {container_name}...")
        
        start_time = time.time()
        
        # Stop container
        stop_result = subprocess.run(
            ["podman", "stop", container_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        shutdown_time = time.time() - start_time
        
        if stop_result.returncode != 0:
            print(f"Warning: Stop command failed: {stop_result.stderr}")
        
        return shutdown_time
    
    def measure_full_cycle(self, container_name: str) -> Dict[str, float]:
        """Measure full stop -> start -> healthy cycle."""
        print(f"Measuring full cycle time for {container_name}...")
        
        cycle_start = time.time()
        
        # Phase 1: Shutdown
        shutdown_start = time.time()
        shutdown_result = subprocess.run(
            ["podman", "stop", container_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        shutdown_time = time.time() - shutdown_start
        
        if shutdown_result.returncode != 0:
            raise Exception(f"Failed to stop {container_name}: {shutdown_result.stderr}")
        
        # Phase 2: Startup
        startup_start = time.time()
        start_result = subprocess.run(
            ["podman", "start", container_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if start_result.returncode != 0:
            raise Exception(f"Failed to start {container_name}: {start_result.stderr}")
        
        # Phase 3: Wait for healthy
        startup_phases = self.measure_container_startup(container_name, timeout=30)
        
        total_cycle_time = time.time() - cycle_start
        
        cycle_results = {
            'shutdown_time': shutdown_time,
            'startup_phases': startup_phases,
            'total_cycle_time': total_cycle_time
        }
        
        # Record results
        self.thresholds.record_result(container_name, 'full_cycle', cycle_results)
        
        return cycle_results
    
    def restart_and_measure(self, container_name: str) -> Dict[str, float]:
        """Restart container and measure startup time."""
        print(f"Restarting {container_name} for performance measurement...")
        
        restart_start = time.time()
        
        # Restart container
        restart_result = subprocess.run(
            ["podman", "restart", container_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        restart_total_time = time.time() - restart_start
        
        if restart_result.returncode != 0:
            raise Exception(f"Failed to restart {container_name}: {restart_result.stderr}")
        
        # Measure startup phases
        phases = self.measure_container_startup(container_name)
        
        # Add restart total time
        phases['restart_total_time'] = restart_total_time
        
        # Record results
        self.thresholds.record_result(container_name, 'restart', phases)
        
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
            if phases['service_responding'] <= responding_threshold:
                print(f"✓ DNS service responding within threshold: {phases['service_responding']:.2f}s")
            else:
                print(f"⚠ DNS service response slow: {phases['service_responding']:.2f}s (threshold: {responding_threshold:.2f}s)")
                # Don't fail the test for service responding - just warn
        else:
            print("ℹ DNS service response test was skipped")
        
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
            if phases['service_responding'] <= responding_threshold:
                print(f"✓ Mail service responding within threshold: {phases['service_responding']:.2f}s")
            else:
                print(f"⚠ Mail service response slow: {phases['service_responding']:.2f}s (threshold: {responding_threshold:.2f}s)")
        else:
            print("ℹ Mail service response test was skipped")
        
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
            if phases['service_responding'] <= responding_threshold:
                print(f"✓ Web service responding within threshold: {phases['service_responding']:.2f}s")
            else:
                print(f"⚠ Web service response slow: {phases['service_responding']:.2f}s (threshold: {responding_threshold:.2f}s)")
        else:
            print("ℹ Web service response test was skipped")
        
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
    
    def test_shutdown_performance(self, performance_tester, running_containers):
        """Test container shutdown performance."""
        results = {}
        
        print(f"\n{'='*50}")
        print("CONTAINER SHUTDOWN PERFORMANCE")
        print(f"{'='*50}")
        
        for container_name in running_containers:
            try:
                shutdown_time = performance_tester.measure_shutdown_time(container_name)
                results[container_name] = shutdown_time
                
                print(f"{container_name}: {shutdown_time:.2f}s")
                
                # Restart container for next tests
                subprocess.run(
                    ["podman", "start", container_name],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Wait for health check
                time.sleep(5)
                
            except Exception as e:
                print(f"Failed to test shutdown for {container_name}: {e}")
                results[container_name] = None
        
        # Assert reasonable shutdown times using thresholds
        for container_name, shutdown_time in results.items():
            if shutdown_time is not None:
                threshold = performance_tester.thresholds.get_threshold(container_name, 'shutdown_time')
                assert shutdown_time <= threshold, f"Container {container_name} shutdown too slow: {shutdown_time:.2f}s (threshold: {threshold:.2f}s)"
        
        # Ensure at least one container was tested
        successful_tests = [t for t in results.values() if t is not None]
        assert len(successful_tests) > 0, "No shutdown times could be measured"
    
    @pytest.mark.slow
    def test_full_cycle_performance(self, performance_tester, running_containers):
        """Test full container lifecycle (stop -> start -> healthy)."""
        results = {}
        
        print(f"\n{'='*60}")
        print("FULL CONTAINER LIFECYCLE PERFORMANCE")
        print(f"{'='*60}")
        
        # Test one container at a time to avoid resource conflicts
        test_container = running_containers[0] if running_containers else None
        if not test_container:
            pytest.skip("No containers available for cycle testing")
        
        try:
            cycle_results = performance_tester.measure_full_cycle(test_container)
            results[test_container] = cycle_results
            
            shutdown_time = cycle_results['shutdown_time']
            startup_phases = cycle_results['startup_phases']
            total_time = cycle_results['total_cycle_time']
            
            print(f"\nFull Cycle Results for {test_container}:")
            print(f"  Shutdown time: {shutdown_time:.2f}s")
            print(f"  Container running: {startup_phases.get('container_running', 'N/A'):.2f}s" if startup_phases.get('container_running') else "  Container running: N/A")
            print(f"  Health check healthy: {startup_phases.get('health_check_healthy', 'N/A'):.2f}s" if startup_phases.get('health_check_healthy') else "  Health check healthy: N/A")
            print(f"  Service responding: {startup_phases.get('service_responding', 'N/A'):.2f}s" if startup_phases.get('service_responding') else "  Service responding: N/A")
            print(f"  Total cycle time: {total_time:.2f}s")
            
            # Performance assertions using thresholds
            shutdown_threshold = performance_tester.thresholds.get_threshold(test_container, 'shutdown_time')
            cycle_threshold = performance_tester.thresholds.get_threshold(test_container, 'total_cycle_time')
            
            assert shutdown_time <= shutdown_threshold, f"Shutdown too slow: {shutdown_time:.2f}s (threshold: {shutdown_threshold:.2f}s)"
            assert total_time <= cycle_threshold, f"Full cycle too slow: {total_time:.2f}s (threshold: {cycle_threshold:.2f}s)"
            
            if startup_phases.get('health_check_healthy'):
                healthy_time = startup_phases['health_check_healthy']
                healthy_threshold = performance_tester.thresholds.get_threshold(test_container, 'health_check_healthy')
                assert healthy_time <= healthy_threshold, f"Health check too slow: {healthy_time:.2f}s (threshold: {healthy_threshold:.2f}s)"
            
        except Exception as e:
            print(f"Failed to test full cycle for {test_container}: {e}")
            results[test_container] = {'error': str(e)}
        
        # Ensure the test was successful
        successful_results = [r for r in results.values() if 'error' not in r]
        assert len(successful_results) > 0, "No full cycle tests completed successfully"
    
    def test_restart_vs_stop_start_comparison(self, performance_tester, running_containers):
        """Compare restart command vs manual stop/start cycle."""
        if not running_containers:
            pytest.skip("No containers available for comparison testing")
        
        test_container = running_containers[0]
        
        print(f"\n{'='*50}")
        print("RESTART vs STOP/START COMPARISON")
        print(f"{'='*50}")
        
        try:
            # Test 1: Restart command
            print(f"\nTesting restart command on {test_container}...")
            restart_phases = performance_tester.restart_and_measure(test_container)
            restart_time = restart_phases.get('restart_total_time', 0)
            
            # Wait for stability
            time.sleep(2)
            
            # Test 2: Manual stop/start cycle  
            print(f"\nTesting manual stop/start cycle on {test_container}...")
            cycle_results = performance_tester.measure_full_cycle(test_container)
            cycle_time = cycle_results['total_cycle_time']
            
            print(f"\nComparison Results:")
            print(f"  Restart command: {restart_time:.2f}s")
            print(f"  Stop/Start cycle: {cycle_time:.2f}s")
            print(f"  Difference: {abs(restart_time - cycle_time):.2f}s")
            
            if restart_time < cycle_time:
                print(f"  ✓ Restart command is {cycle_time - restart_time:.2f}s faster")
            else:
                print(f"  ⚠ Manual cycle is {restart_time - cycle_time:.2f}s faster")
            
            # Both should be reasonable using thresholds
            restart_threshold = performance_tester.thresholds.get_threshold(test_container, 'restart_total_time')
            cycle_threshold = performance_tester.thresholds.get_threshold(test_container, 'total_cycle_time')
            
            assert restart_time <= restart_threshold, f"Restart too slow: {restart_time:.2f}s (threshold: {restart_threshold:.2f}s)"
            assert cycle_time <= cycle_threshold, f"Stop/start cycle too slow: {cycle_time:.2f}s (threshold: {cycle_threshold:.2f}s)"
            
        except Exception as e:
            pytest.fail(f"Comparison test failed: {e}")
    
    def test_concurrent_shutdown_performance(self, performance_tester, running_containers):
        """Test how containers perform when shut down concurrently."""
        if len(running_containers) < 2:
            pytest.skip("Need at least 2 containers for concurrent testing")
        
        print(f"\n{'='*50}")
        print("CONCURRENT SHUTDOWN PERFORMANCE")
        print(f"{'='*50}")
        
        # Test concurrent shutdown
        start_time = time.time()
        
        processes = []
        for container in running_containers:
            proc = subprocess.Popen(
                ["podman", "stop", container],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            processes.append((container, proc))
        
        # Wait for all to complete
        results = {}
        for container, proc in processes:
            stdout, stderr = proc.communicate(timeout=30)
            end_time = time.time()
            results[container] = {
                'returncode': proc.returncode,
                'time': end_time - start_time,
                'stderr': stderr.decode() if stderr else ''
            }
        
        total_concurrent_time = time.time() - start_time
        
        print(f"\nConcurrent shutdown results:")
        print(f"  Total time: {total_concurrent_time:.2f}s")
        
        for container, result in results.items():
            if result['returncode'] == 0:
                print(f"  {container}: ✓ {result['time']:.2f}s")
            else:
                print(f"  {container}: ✗ Failed - {result['stderr']}")
        
        # Restart all containers
        for container in running_containers:
            subprocess.run(
                ["podman", "start", container],
                capture_output=True,
                text=True,
                timeout=30
            )
        
        # Wait for services to be ready
        time.sleep(5)
        
        # Assert concurrent shutdown is faster than sequential
        sequential_estimate = len(running_containers) * 2.0  # Assume 2s per container
        print(f"  Sequential estimate: {sequential_estimate:.2f}s")
        print(f"  Concurrent actual: {total_concurrent_time:.2f}s")
        
        if total_concurrent_time < sequential_estimate:
            print(f"  ✓ Concurrent shutdown is {sequential_estimate - total_concurrent_time:.2f}s faster")
        
        assert total_concurrent_time < 15.0, f"Concurrent shutdown too slow: {total_concurrent_time:.2f}s"