# PodServe Makefile

# Implementation selection (default: shell-based)
IMPL ?= shell-based

.PHONY: help install test test-unit test-integration test-container test-performance test-all clean build lint format check dev-setup benchmark benchmark-quick benchmark-shutdown performance-report logs status teardown deploy

# Default target
help:
	@echo "PodServe Development Commands"
	@echo "============================"
	@echo ""
	@echo "Implementation: $(IMPL)"
	@echo "  Set IMPL variable to switch implementations:"
	@echo "  make build IMPL=python-unified"
	@echo ""
	@echo "Setup:"
	@echo "  dev-setup    - Set up development environment (venv, deps, pre-commit)"
	@echo "  install      - Install package in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  test         - Run all tests"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-integration - Run integration tests (requires containers)"
	@echo "  test-container   - Run container-specific tests"
	@echo "  test-performance - Run performance tests"
	@echo "  test-mail        - Run mail integration tests"
	@echo "  test-coverage    - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint         - Run linting (flake8, mypy)"
	@echo "  format       - Format code (black, isort)"
	@echo "  check        - Run all code quality checks"
	@echo ""
	@echo "Container Management:"
	@echo "  build        - Build all container images"
	@echo "  deploy       - Deploy simple pod configuration"
	@echo "  teardown     - Stop and remove all pods/containers"
	@echo "  logs         - Show container logs"
	@echo "  status       - Show pod, container, and volume status"
	@echo ""
	@echo "Performance:"
	@echo "  benchmark    - Run performance benchmarks"
	@echo "  benchmark-quick - Run quick performance test"
	@echo "  benchmark-shutdown - Test shutdown performance"
	@echo "  performance-report - Show performance report"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean        - Remove build artifacts and cache"

# Development setup
dev-setup: venv/.created
	@echo "Development environment ready!"

venv/.created:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip setuptools wheel
	. venv/bin/activate && pip install -e ".[test,dev]"
	touch venv/.created

install: venv/.created
	venv/bin/pip install -e ".[test,dev]"

# Testing
test: venv/.created
	venv/bin/pytest shared/tests/

test-unit: venv/.created
	venv/bin/pytest shared/tests/ -m "not integration and not container" -v

test-integration: venv/.created
	venv/bin/pytest shared/tests/ -m integration -v

test-container: venv/.created
	venv/bin/pytest shared/tests/ -m container -v

test-performance: venv/.created
	venv/bin/pytest shared/tests/test_container_performance.py -v

test-mail: venv/.created
	venv/bin/pytest shared/tests/test_mail_integration.py -v

test-coverage: venv/.created
	venv/bin/pytest shared/tests/ --cov=podserve --cov-report=html --cov-report=term-missing

test-all: venv/.created
	venv/bin/pytest shared/tests/ -v --tb=short

# Code quality
lint: venv/.created
	venv/bin/flake8 implementations/$(IMPL)/src/ shared/tests/
	venv/bin/mypy implementations/$(IMPL)/src/

format: venv/.created
	venv/bin/black implementations/$(IMPL)/src/ shared/tests/
	venv/bin/isort implementations/$(IMPL)/src/ shared/tests/

check: lint
	@echo "All code quality checks passed!"

# Container operations
build:
	@if [ -f implementations/$(IMPL)/docker/build.sh ]; then \
		cd implementations/$(IMPL)/docker && ./build.sh; \
	else \
		echo "No build script found for implementation: $(IMPL)"; \
		exit 1; \
	fi

deploy:
	@if [ -f implementations/$(IMPL)/deploy/simple.yaml ]; then \
		podman play kube implementations/$(IMPL)/deploy/simple.yaml; \
	else \
		echo "No deployment file found for implementation: $(IMPL)"; \
		exit 1; \
	fi

teardown:
	-podman pod stop --all
	-podman pod rm --all
	-podman container stop --all
	-podman container rm --all

logs:
	@echo "=== Apache Logs ==="
	-podman logs podserve-simple-apache
	@echo ""
	@echo "=== Mail Logs ==="
	-podman logs podserve-simple-mail
	@echo ""
	@echo "=== DNS Logs ==="
	-podman logs podserve-simple-dns

# Performance and benchmarking
benchmark:
	@if [ -f implementations/$(IMPL)/scripts/benchmark.sh ]; then \
		implementations/$(IMPL)/scripts/benchmark.sh; \
	else \
		echo "No benchmark script found for implementation: $(IMPL)"; \
		exit 1; \
	fi

benchmark-quick:
	@if [ -f implementations/$(IMPL)/scripts/benchmark.sh ]; then \
		implementations/$(IMPL)/scripts/benchmark.sh quick; \
	else \
		echo "No benchmark script found for implementation: $(IMPL)"; \
		exit 1; \
	fi

benchmark-shutdown:
	@if [ -f implementations/$(IMPL)/scripts/benchmark.sh ]; then \
		implementations/$(IMPL)/scripts/benchmark.sh shutdown; \
	else \
		echo "No benchmark script found for implementation: $(IMPL)"; \
		exit 1; \
	fi

performance-report: venv/.created
	venv/bin/python shared/tools/performance_thresholds.py report

status:
	@echo "=== Pod Status ==="
	podman pod ps
	@echo ""
	@echo "=== Container Status ==="
	podman ps -a
	@echo ""
	@echo "=== Volume Status ==="
	podman volume ls

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean
	rm -rf venv/

# Quick development cycle
dev: format lint test-unit
	@echo "Development cycle complete!"

# Full CI-like check
ci: format lint test-all
	@echo "All CI checks passed!"