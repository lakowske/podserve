# Development Tools

This directory contains performance monitoring and development tools.

## Files

- **performance_thresholds.py** - Performance threshold management and reporting
- **performance_results.json** - Performance test results data

## Usage

```bash
# Generate performance report
python tools/performance_thresholds.py report

# Show optimization suggestions
python tools/performance_thresholds.py suggest

# Display current thresholds
python tools/performance_thresholds.py thresholds
```

## Integration

Performance tools are integrated with testing and make targets:

```bash
# Via make targets
make performance-report

# Via test suite
make test-performance
```

## Performance Thresholds

The system tracks performance metrics for:
- Container startup times
- Health check response times
- Service response times  
- Shutdown times
- Full lifecycle times