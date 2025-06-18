#\!/bin/bash
# Fast tests (no coverage, parallel)
if [ "$1" = "fast" ]; then
    venv/bin/pytest tests/ -n auto --tb=line -q
# Coverage tests (sequential, with coverage)
elif [ "$1" = "cov" ]; then
    venv/bin/pytest tests/ --cov=podserve --cov-report=term-missing --cov-report=html:htmlcov -v
# Default: fast tests
else
    venv/bin/pytest tests/ -n auto --tb=line -q
fi
