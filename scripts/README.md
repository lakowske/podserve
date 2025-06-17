# Scripts

This directory contains utility scripts for development and testing.

## Files

- **benchmark.sh** - Performance benchmarking and testing script
- **test.sh** - Development testing script

## Usage

```bash
# Run performance benchmarks
./scripts/benchmark.sh

# Quick performance test
./scripts/benchmark.sh quick

# Shutdown performance test
./scripts/benchmark.sh shutdown

# Full lifecycle test
./scripts/benchmark.sh cycle
```

## Integration

These scripts are integrated with the Makefile:

```bash
# Via make targets
make benchmark
make benchmark-quick
make benchmark-shutdown
```