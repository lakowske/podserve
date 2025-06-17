#!/bin/bash
# Container performance benchmark script

set -e

echo "PodServe Container Performance Benchmark"
echo "========================================"

# Check if containers are running
echo "Checking for running containers..."
CONTAINERS=$(podman ps --filter "name=podserve" --format "{{.Names}}" | grep -v "^$" || true)

if [ -z "$CONTAINERS" ]; then
    echo "No PodServe containers running. Starting pod..."
    podman play kube deploy/simple.yaml
    echo "Waiting for containers to start..."
    sleep 10
fi

# Run performance tests
echo ""
echo "Running container performance tests..."
echo "======================================"

# Performance-only tests
if [ "$1" = "quick" ]; then
    echo "Running quick performance tests (DNS only)..."
    venv/bin/pytest tests/test_container_performance.py::TestContainerPerformance::test_dns_startup_performance -v -s
elif [ "$1" = "full" ]; then
    echo "Running full performance benchmark..."
    venv/bin/pytest tests/test_container_performance.py::TestContainerPerformance::test_all_containers_startup_benchmark -v -s
elif [ "$1" = "health" ]; then
    echo "Running health check performance tests..."
    venv/bin/pytest tests/test_container_performance.py::TestContainerPerformance::test_health_check_response_times -v -s
elif [ "$1" = "shutdown" ]; then
    echo "Running shutdown performance tests..."
    venv/bin/pytest tests/test_container_performance.py::TestContainerPerformance::test_shutdown_performance -v -s
elif [ "$1" = "cycle" ]; then
    echo "Running full lifecycle tests (may take a while)..."
    venv/bin/pytest tests/test_container_performance.py::TestContainerPerformance::test_full_cycle_performance -v -s
elif [ "$1" = "compare" ]; then
    echo "Comparing restart vs stop/start performance..."
    venv/bin/pytest tests/test_container_performance.py::TestContainerPerformance::test_restart_vs_stop_start_comparison -v -s
elif [ "$1" = "concurrent" ]; then
    echo "Testing concurrent shutdown performance..."
    venv/bin/pytest tests/test_container_performance.py::TestContainerPerformance::test_concurrent_shutdown_performance -v -s
else
    echo "Running all performance tests..."
    venv/bin/pytest tests/test_container_performance.py -v -s -m performance
fi

echo ""
echo "Performance benchmark complete!"
echo ""
echo "Usage:"
echo "  ./benchmark.sh            - Run all performance tests"
echo "  ./benchmark.sh quick      - Run quick DNS performance test"
echo "  ./benchmark.sh full       - Run full startup benchmark"
echo "  ./benchmark.sh health     - Run health check performance tests"
echo "  ./benchmark.sh shutdown   - Run shutdown performance tests"
echo "  ./benchmark.sh cycle      - Run full lifecycle tests (slow)"
echo "  ./benchmark.sh compare    - Compare restart vs stop/start"
echo "  ./benchmark.sh concurrent - Test concurrent shutdown"