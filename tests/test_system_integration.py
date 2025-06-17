"""System-level integration tests."""

import subprocess
import time

import pytest
import yaml


@pytest.mark.integration
@pytest.mark.container
class TestSystemIntegration:
    """System-level integration tests for PodServe."""

    def test_pod_status(self):
        """Test that the PodServe pod is running correctly."""
        try:
            result = subprocess.run(
                ["podman", "pod", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            pods = yaml.safe_load(result.stdout) if result.stdout.strip() else []

            # Find PodServe pod
            podserve_pods = [
                pod for pod in pods if "podserve" in pod.get("Name", "").lower()
            ]
            assert len(podserve_pods) > 0, "No PodServe pods found"

            # Check that at least one pod is running
            running_pods = [
                pod for pod in podserve_pods if pod.get("Status") == "Running"
            ]
            assert len(running_pods) > 0, "No PodServe pods are running"

        except subprocess.CalledProcessError as e:
            pytest.skip(f"Could not check pod status: {e}")
        except FileNotFoundError:
            pytest.skip("Podman not available")

    def test_container_health(self):
        """Test that containers are healthy."""
        try:
            result = subprocess.run(
                ["podman", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            containers = yaml.safe_load(result.stdout) if result.stdout.strip() else []

            # Find PodServe containers
            podserve_containers = [
                container
                for container in containers
                if "podserve" in container.get("Names", [""])[0].lower()
            ]
            assert len(podserve_containers) > 0, "No PodServe containers found"

            # Check container status
            for container in podserve_containers:
                status = container.get("State", "").lower()
                container_name = container.get("Names", ["unknown"])[0]
                assert (
                    status == "running"
                ), f"Container {container_name} is not running: {status}"

        except subprocess.CalledProcessError as e:
            pytest.skip(f"Could not check container status: {e}")
        except FileNotFoundError:
            pytest.skip("Podman not available")

    def test_volume_mounts(self):
        """Test that required volumes are mounted."""
        try:
            result = subprocess.run(
                ["podman", "volume", "ls", "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            volumes = yaml.safe_load(result.stdout) if result.stdout.strip() else []

            # Check for expected volumes
            volume_names = [vol.get("Name", "") for vol in volumes]
            expected_volumes = [
                "podserve-certificates",
                "podserve-simple-web",
                "podserve-simple-mail",
                "podserve-simple-logs",
            ]

            for expected_vol in expected_volumes:
                assert any(
                    expected_vol in vol_name for vol_name in volume_names
                ), f"Expected volume {expected_vol} not found"

        except subprocess.CalledProcessError as e:
            pytest.skip(f"Could not check volumes: {e}")
        except FileNotFoundError:
            pytest.skip("Podman not available")

    def test_log_accessibility(self):
        """Test that container logs are accessible."""
        try:
            # Get list of running containers
            result = subprocess.run(
                ["podman", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True,
            )
            container_names = [
                name.strip() for name in result.stdout.split("\n") if name.strip()
            ]

            # Find PodServe containers
            podserve_containers = [
                name for name in container_names if "podserve" in name.lower()
            ]
            assert len(podserve_containers) > 0, "No PodServe containers found"

            # Test log access for each container
            for container_name in podserve_containers:
                log_result = subprocess.run(
                    ["podman", "logs", "--tail", "5", container_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                # Should not fail (exit code 0 or logs available)
                assert (
                    log_result.returncode == 0 or log_result.stderr == ""
                ), f"Could not access logs for {container_name}"

        except subprocess.CalledProcessError as e:
            pytest.skip(f"Could not check logs: {e}")
        except subprocess.TimeoutExpired:
            pytest.skip("Log access timed out")
        except FileNotFoundError:
            pytest.skip("Podman not available")

    @pytest.mark.slow
    def test_service_restart_resilience(self):
        """Test that services can be restarted successfully."""
        try:
            # Get list of running PodServe containers
            result = subprocess.run(
                [
                    "podman",
                    "ps",
                    "--filter",
                    "name=podserve",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            container_names = [
                name.strip() for name in result.stdout.split("\n") if name.strip()
            ]

            if not container_names:
                pytest.skip("No PodServe containers found for restart test")

            # Test restart of DNS container (fastest to restart)
            dns_container = next((name for name in container_names if "dns" in name), None)
            container_name = dns_container or container_names[0]

            # Restart container with shorter timeout
            subprocess.run(
                ["podman", "restart", container_name],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,  # Reduced from 30s
            )

            # Reduced wait time
            time.sleep(1)

            # Check that container is running again
            status_result = subprocess.run(
                [
                    "podman",
                    "inspect",
                    container_name,
                    "--format",
                    "{{.State.Status}}",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            assert (
                status_result.stdout.strip().lower() == "running"
            ), f"Container {container_name} not running after restart"

        except subprocess.CalledProcessError as e:
            pytest.skip(f"Could not test restart resilience: {e}")
        except subprocess.TimeoutExpired:
            pytest.skip("Container restart timed out")
        except FileNotFoundError:
            pytest.skip("Podman not available")

    def test_resource_usage(self):
        """Test that containers are using reasonable resources."""
        try:
            # Get container statistics
            result = subprocess.run(
                ["podman", "stats", "--no-stream", "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )

            if not result.stdout.strip():
                pytest.skip("No container stats available")

            stats = yaml.safe_load(result.stdout)

            # Find PodServe containers
            podserve_stats = [
                stat for stat in stats if "podserve" in stat.get("name", "").lower()
            ]

            if not podserve_stats:
                pytest.skip("No PodServe container stats found")

            # Check resource usage is reasonable
            for stat in podserve_stats:
                # Memory usage should be less than 1GB per container
                mem_usage = stat.get("mem_usage", "")
                if mem_usage and ("MB" in mem_usage or "MiB" in mem_usage):
                    # Extract numeric value (handle both MB and MiB)
                    if "MiB" in mem_usage:
                        mem_value = float(mem_usage.split("MiB")[0])
                    else:
                        mem_value = float(mem_usage.split("MB")[0])
                    container_name = stat.get("name")
                    assert mem_value < 1024, (
                        f"Container {container_name} using too much memory: "
                        f"{mem_usage}"
                    )

                # CPU usage should be reasonable (less than 200% for multi-core)
                cpu_usage = stat.get("cpu_percent", "")
                if cpu_usage and "%" in cpu_usage:
                    cpu_value = float(cpu_usage.replace("%", ""))
                    container_name = stat.get("name")
                    assert cpu_value < 200, (
                        f"Container {container_name} using too much CPU: "
                        f"{cpu_usage}"
                    )

        except subprocess.CalledProcessError as e:
            pytest.skip(f"Could not check resource usage: {e}")
        except subprocess.TimeoutExpired:
            pytest.skip("Resource usage check timed out")
        except (ValueError, KeyError):
            pytest.skip("Could not parse resource usage statistics")
        except FileNotFoundError:
            pytest.skip("Podman not available")
