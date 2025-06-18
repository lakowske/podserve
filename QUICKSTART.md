# PodServe Quick Start Guide

Welcome to PodServe - an integrated server pod providing web, mail, and DNS services using Podman.

## 🚀 For Claude/AI Assistants
**Start here**: [docs/PRINCIPLES.md](docs/PRINCIPLES.md) - Contains critical principles and common pitfalls to avoid.

## 📚 Documentation Map

### Core Documentation (Read in Order)
1. **[Core Principles](docs/PRINCIPLES.md)** - Critical principles and lessons learned
2. **[Podman Best Practices](docs/PODMAN-BEST-PRACTICES.md)** - Container and pod management patterns
3. **[Permissions Guide](docs/PERMISSIONS-GUIDE.md)** - UID/GID and volume permission handling
   - **[Developer-Friendly Permissions](docs/DEVELOPER-FRIENDLY-PERMISSIONS.md)** - Use your UID/GID by default
   - **[User Namespace Comparison](docs/USER-NAMESPACE-COMPARISON.md)** - Namespace remapping vs explicit UID/GID
4. **[Service Development Guide](docs/SERVICE-DEVELOPMENT-GUIDE.md)** - Systematic one-by-one service development
5. **[Debugging Guide](docs/DEBUGGING-GUIDE.md)** - Common issues and solutions
6. **[Architecture Decisions](docs/ARCHITECTURE-DECISIONS.md)** - Why we made certain choices

### Implementation Documentation
- **[Shell-based](implementations/shell-based/)** - Original stable implementation
  - [Overview](implementations/shell-based/README.md)
  - [Lessons Learned](implementations/shell-based/LESSONS-LEARNED.md)
- **[Python-unified](implementations/python-unified/)** - Modern Python framework (active development)
  - [Overview](implementations/python-unified/README.md)
  - [Implementation Guide](services-docs/python-implementation-guide.md)
  - [Lessons Learned](implementations/python-unified/LESSONS-LEARNED.md)

### Service Documentation
- **[Service Specifications](services-docs/)** - Detailed specifications for each service
- **[Shared Resources](shared/)** - Tests, tools, and general documentation

## 🛠️ Quick Commands

```bash
# Build containers (default: shell-based)
make build

# Build specific implementation
make build IMPL=python-unified

# Deploy pod
make deploy IMPL=python-unified

# Run tests
make test

# View logs
podman logs podserve-simple-apache
podman logs podserve-simple-mail
podman logs podserve-simple-dns
```

## 🎯 Current Development Focus
- **Active**: Python unified implementation
- **Goal**: Provide better debugging, templating, and maintainability

## 🔧 Development Workflow

### For Shell-based Implementation
```bash
cd implementations/shell-based
# Edit configurations directly
# Rebuild and redeploy to test
```

### For Python Implementation
```bash
# Use development mode with host mounts and your UID/GID
cd implementations/python-unified/docker
./build-dev.sh all  # Builds with your UID/GID
cd ..
podman play kube deploy/dev-permissions.yaml  # Uses your permissions

# Edit Python code on host
# Changes reflect immediately in containers
# All files owned by your user - no permission issues!
```

## 📋 Prerequisites
- Podman 4.0+ installed
- Basic understanding of containers and pods
- Familiarity with web, mail, and DNS services

## 🚨 Important Notes
1. **Always** consult official service documentation before complex troubleshooting
2. **Always** verify return types match expected patterns (bool vs None)
3. **Always** use stdout/stderr for container logging
4. **Always** test services in isolation before integration

## 📖 Next Steps
1. Read [Core Principles](docs/PRINCIPLES.md) to understand critical patterns
2. Choose an implementation approach
3. Follow the implementation-specific guide
4. Run tests to verify functionality

## 🤝 Contributing
When adding new learnings or principles:
- Implementation-specific lessons go in `implementations/*/LESSONS-LEARNED.md`
- Universal principles go in `docs/PRINCIPLES.md`
- Debugging patterns go in `docs/DEBUGGING-GUIDE.md`