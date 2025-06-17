# PodServe Makefile

.PHONY: help install test test-unit test-integration test-all clean build lint format check dev-setup

# Default target
help:
	@echo "PodServe Development Commands"
	@echo "============================"
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
	venv/bin/pytest

test-unit: venv/.created
	venv/bin/pytest -m "not integration and not container" -v

test-integration: venv/.created
	venv/bin/pytest -m integration -v

test-container: venv/.created
	venv/bin/pytest -m container -v

test-coverage: venv/.created
	venv/bin/pytest --cov=podserve --cov-report=html --cov-report=term-missing

test-all: venv/.created
	venv/bin/pytest -v --tb=short

# Code quality
lint: venv/.created
	venv/bin/flake8 src/ tests/
	venv/bin/mypy src/

format: venv/.created
	venv/bin/black src/ tests/
	venv/bin/isort src/ tests/

check: lint
	@echo "All code quality checks passed!"

# Container operations
build:
	cd docker && ./build.sh

deploy:
	podman play kube simple.yaml

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