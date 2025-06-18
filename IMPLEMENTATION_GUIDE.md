# Implementation Guide

## Project Organization

PodServe now supports multiple implementation approaches to experiment with different architectures.

### Directory Structure

- **`services-docs/`** - Service implementation guides and specifications
- **`implementations/`** - Different implementation attempts
  - `shell-based/` - Original shell script implementation (stable)
  - `python-unified/` - Python framework implementation (in development)
- **`shared/`** - Resources shared across all implementations
  - `docs/` - General documentation
  - `tests/` - Test suite
  - `tools/` - Development tools

### Working with Implementations

#### Switching Implementations

```bash
# Default (shell-based)
make build
make deploy

# Specific implementation
make build IMPL=python-unified
make deploy IMPL=python-unified

# Set for session
export IMPL=python-unified
make build
```

#### Creating a New Implementation

1. Create directory: `implementations/my-new-approach/`
2. Add subdirectories: `docker/`, `src/`, `deploy/`
3. Follow patterns in `services-docs/`
4. Create `README.md` explaining the approach

### Development Workflow

#### For shell-based:
```bash
cd implementations/shell-based
# Edit configurations directly
# Rebuild and redeploy to test
```

#### For python-unified:
```bash
# Use development mode with host mounts
make deploy IMPL=python-unified  # Uses dev.yaml
# Edit Python code on host
# Changes reflect immediately in containers
```

### Testing

Tests in `shared/tests/` work across all implementations:

```bash
# Test current implementation
make test

# Test specific implementation
make test IMPL=python-unified
```

### Guidelines

1. **Keep implementations self-contained** - Each should work independently
2. **Share tests and tools** - Ensure consistency across approaches
3. **Document differences** - Explain unique aspects in implementation README
4. **Follow service specs** - Use `services-docs/` as the source of truth

### Logging Strategy for Python Implementation

#### Volume Structure
Each service will have standard volumes:
- `/data/config` - Configuration files
- `/data/logs` - Log files for debugging
- `/data/state` - Persistent state data

#### Dual Logging Approach
Services output to both stdout/stderr (container best practice) and files:

1. **Console Output** - For `podman logs` command
2. **File Output** - To `/data/logs/` for Claude Code inspection

This enables:
- Container-native log viewing
- In-container debugging with Claude Code
- Log persistence across restarts
- Historical log analysis

#### Implementation in BaseService
The Python framework includes automatic dual logging setup with:
- Rotating file handlers (10MB max, 5 backups)
- Consistent formatting across all services
- Service-specific log files
- Configurable log levels via environment variables