# Service Development Guide: One-by-One with Validation

This guide establishes a systematic approach to developing PodServe services individually with proper validation at each step, ensuring early detection of issues and reliable integration.

## 🎯 Core Philosophy

**Develop services in isolation first, then integrate systematically.**

Each service must be fully functional, tested, and meet performance criteria before combining with others. This approach catches issues early when they're easier to debug and fix.

## 📋 Six-Phase Development Process

### Phase 1: Service Planning and Design

**Goal**: Define comprehensive service requirements before writing code.

#### Planning Checklist
- [ ] **Service Scope Definition**
  - What does this service do?
  - What ports/protocols does it use?
  - What data does it need to persist?
  - What configuration is required?

- [ ] **Health Check Strategy**
  - How will we know the service is healthy?
  - What are the specific health check endpoints/commands?
  - What's the difference between liveness and readiness?
  - How long should health checks take?

- [ ] **Performance Targets**
  - What's acceptable startup time?
  - What's acceptable memory usage?
  - What response time targets exist?
  - What throughput is expected?

- [ ] **Testing Strategy**
  - How will we test this service in isolation?
  - What integration points need testing?
  - What failure modes should we test?
  - What performance benchmarks will we run?

- [ ] **Dependencies and Integration**
  - What other services does this depend on?
  - What services will depend on this?
  - What shared volumes/configs are needed?
  - What network communication is required?

#### Example: DNS Service Planning

```markdown
## DNS Service Plan

**Scope**: Recursive DNS resolution for pod-internal services
**Ports**: 53/tcp, 53/udp  
**Data**: Zone files, cache data
**Config**: Forwarders, recursion settings, logging

**Health Check Strategy**:
- Liveness: `dig @localhost google.com` (< 2 seconds)
- Readiness: `dig @localhost localhost` (internal resolution)
- Startup time target: < 5 seconds

**Performance Targets**:
- Memory: < 100MB baseline
- Query response: < 100ms for cached
- Startup time: < 5 seconds
- Throughput: > 1000 queries/second

**Testing Strategy**:
- Unit: Query resolution, configuration validation
- Integration: Pod internal name resolution
- Performance: Query load testing
- Failure: Forwarder unavailable, config errors

**Dependencies**: None (foundational service)
**Dependents**: All other services for name resolution
```

### Phase 2: Isolated Service Development

**Goal**: Build and validate the service in complete isolation.

#### Development Checklist
- [ ] **Container Implementation**
  - Dockerfile follows base image patterns
  - Service runs as appropriate user
  - Proper signal handling implemented
  - Environment variable configuration

- [ ] **Service Class Implementation** (Python services)
  - Inherits from BaseService
  - Implements configure() → bool
  - Implements start_processes() → bool
  - Returns True/False correctly (not None!)
  - Comprehensive logging with DEBUG level

- [ ] **Health Check Implementation**
  - Simple, fast health check commands
  - Both liveness and readiness checks
  - Clear success/failure criteria
  - Proper error reporting

- [ ] **Configuration Management**
  - Template rendering works correctly
  - All required environment variables handled
  - Default values for development
  - Configuration validation

#### Isolation Testing Commands

```bash
# Test service in complete isolation
podman run --rm -e LOG_LEVEL=DEBUG \
  localhost/podserve-SERVICE:latest SERVICE

# Test health checks
podman run --rm localhost/podserve-SERVICE:latest \
  /usr/local/bin/health-check.sh

# Test configuration rendering
podman run --rm -e DOMAIN=test.local \
  localhost/podserve-SERVICE:latest \
  python3 -c "from podserve.services.SERVICE import SERVICEService; s = SERVICEService(debug=True); print(s.configure())"

# Test resource usage
podman stats --no-stream $(podman run -d localhost/podserve-SERVICE:latest)
```

#### Success Criteria for Phase 2
- [ ] Service starts consistently (5/5 attempts)
- [ ] Health checks pass reliably
- [ ] Configuration templates render correctly
- [ ] Resource usage within targets
- [ ] Logs show clean startup sequence
- [ ] Service handles SIGTERM gracefully

### Phase 3: Performance Baseline and Validation

**Goal**: Establish performance baselines and validate against targets.

#### Performance Testing
```bash
# Memory usage baseline
echo "=== Memory Usage Test ==="
container_id=$(podman run -d localhost/podserve-SERVICE:latest)
sleep 10
podman stats --no-stream $container_id
podman stop $container_id

# Startup time measurement
echo "=== Startup Time Test ==="
for i in {1..5}; do
  time_start=$(date +%s.%N)
  container_id=$(podman run -d localhost/podserve-SERVICE:latest)
  
  # Wait for health check to pass
  while ! podman exec $container_id /usr/local/bin/health-check.sh; do
    sleep 0.1
  done
  
  time_end=$(date +%s.%N)
  startup_time=$(echo "$time_end - $time_start" | bc)
  echo "Startup attempt $i: ${startup_time}s"
  
  podman stop $container_id
done

# Service-specific performance tests
bash tests/performance/test-SERVICE-performance.sh
```

#### Performance Documentation Template
```markdown
## SERVICE Performance Baseline

**Test Date**: 2024-01-XX
**Image**: localhost/podserve-SERVICE:latest
**Environment**: Development (8GB RAM, 4 CPU)

### Results:
- **Memory Usage**: XXX MB (target: < XXX MB) ✅/❌
- **Startup Time**: X.X seconds (target: < X seconds) ✅/❌ 
- **Service Response**: XXX ms (target: < XXX ms) ✅/❌
- **Throughput**: XXX requests/sec (target: > XXX) ✅/❌

### Issues Found:
- Issue 1: Description and resolution
- Issue 2: Description and resolution

### Next Steps:
- [ ] Performance optimization needed
- [ ] Ready for integration testing
```

#### Success Criteria for Phase 3
- [ ] All performance targets met or documented variance
- [ ] No memory leaks during extended run (1 hour)
- [ ] Restart recovery time acceptable
- [ ] Resource usage predictable and stable

### Phase 4: Integration Planning

**Goal**: Plan how this service will integrate with existing services.

#### Integration Strategy
Before combining services, plan the integration:

1. **Dependency Order**: Which service should start first?
2. **Communication Patterns**: How will services interact?
3. **Shared Resources**: What volumes/configs are shared?
4. **Failure Scenarios**: What happens if this service fails?

#### Common Integration Patterns

##### Pattern 1: Service Requiring DNS
```yaml
# Integration test: SERVICE + DNS
spec:
  containers:
  - name: dns
    image: localhost/podserve-dns:latest
    # Start DNS first
  - name: SERVICE  
    image: localhost/podserve-SERVICE:latest
    # Depends on DNS for name resolution
```

Test plan:
- [ ] DNS starts and becomes ready
- [ ] SERVICE starts and can resolve names
- [ ] SERVICE functionality works with DNS resolution
- [ ] DNS failure recovery testing

##### Pattern 2: Service Requiring SSL Certificates
```yaml
# Integration test: SERVICE + Certificate Provider
spec:
  initContainers:
  - name: cert-setup
    # Generate or copy certificates
  containers:
  - name: SERVICE
    # Uses certificates from shared volume
```

Test plan:
- [ ] Certificates available before SERVICE starts
- [ ] SERVICE loads certificates correctly
- [ ] SSL/TLS functionality works
- [ ] Certificate renewal scenarios

##### Pattern 3: Service Providing Web Interface
```yaml
# Integration test: SERVICE + Apache
spec:
  containers:
  - name: SERVICE
    # Provides API/interface
  - name: apache
    # Proxies to SERVICE
```

Test plan:
- [ ] SERVICE API accessible internally
- [ ] Apache proxy configuration works
- [ ] End-to-end web requests succeed
- [ ] Load balancing (if applicable)

### Phase 5: Service Combination and Testing

**Goal**: Systematically combine services and validate each combination.

#### Integration Testing Strategy

**Start small and grow systematically:**

1. **Pairs First**: Test SERVICE with one other service
2. **Triplets Next**: Add a third service
3. **Full Integration**: All services together

```bash
# Example: Adding mail service to existing apache + dns

# Step 1: Test mail + dns (if mail needs DNS)
podman play kube test-configs/mail-dns.yaml
bash tests/integration/test-mail-dns.sh

# Step 2: Test mail + apache (if mail provides web interface)  
podman play kube test-configs/mail-apache.yaml
bash tests/integration/test-mail-apache.sh

# Step 3: Test mail + dns + apache (full triplet)
podman play kube test-configs/mail-dns-apache.yaml
bash tests/integration/test-mail-dns-apache.sh
```

#### Integration Test Checklist (per combination)
- [ ] **Startup Order**: Services start in correct sequence
- [ ] **Health Checks**: All services report healthy
- [ ] **Communication**: Inter-service communication works
- [ ] **Shared Resources**: No volume/config conflicts
- [ ] **Performance**: Combined performance acceptable
- [ ] **Failure Recovery**: Services recover from restarts
- [ ] **Resource Usage**: Total resource usage within limits

#### Integration Testing Commands
```bash
# Full integration test script
#!/bin/bash
set -e

echo "=== Testing SERVICE Integration ==="

# Deploy the combination
podman play kube test-configs/SERVICE-integration.yaml

# Wait for all services to be ready
for service in dns apache SERVICE; do
  echo "Waiting for $service to be ready..."
  while ! podman exec podserve-test-$service /usr/local/bin/health-check.sh; do
    sleep 1
  done
  echo "$service is ready ✅"
done

# Run integration tests
bash tests/integration/test-SERVICE-integration.sh

# Check resource usage
echo "=== Resource Usage ==="
podman pod stats podserve-test

# Cleanup
podman play kube --down test-configs/SERVICE-integration.yaml

echo "Integration test completed ✅"
```

### Phase 6: Production Readiness

**Goal**: Ensure the service is ready for production deployment.

#### Production Readiness Checklist
- [ ] **Documentation Complete**
  - Service purpose and functionality documented
  - Configuration options documented
  - Health check endpoints documented
  - Troubleshooting guide updated
  - Performance characteristics documented

- [ ] **Security Review**
  - Runs with minimal required privileges
  - No secrets in environment variables
  - Proper file permissions
  - Network security validated

- [ ] **Operational Readiness**
  - Monitoring/alerting configured
  - Log levels appropriate for production
  - Backup/restore procedures documented
  - Upgrade procedures tested

- [ ] **Integration Testing Complete**
  - All service combinations tested
  - Performance under load validated
  - Failure scenarios tested
  - Recovery procedures validated

## 🔧 Validation Tools and Scripts

### Automated Validation Script
```bash
#!/bin/bash
# validate-service.sh - Automated service validation

SERVICE_NAME=$1
PHASE=${2:-all}

validate_isolation() {
  echo "=== Phase 2: Isolation Testing ==="
  
  # Test basic functionality
  echo "Testing basic service startup..."
  if ! podman run --rm localhost/podserve-$SERVICE_NAME:latest timeout 30 $SERVICE_NAME; then
    echo "❌ Service failed to start"
    return 1
  fi
  
  # Test health checks
  echo "Testing health checks..."
  if ! podman run --rm localhost/podserve-$SERVICE_NAME:latest /usr/local/bin/health-check.sh; then
    echo "❌ Health check failed"
    return 1
  fi
  
  echo "✅ Isolation testing passed"
}

validate_performance() {
  echo "=== Phase 3: Performance Testing ==="
  
  # Startup time test
  startup_times=()
  for i in {1..3}; do
    start_time=$(date +%s.%N)
    container_id=$(podman run -d localhost/podserve-$SERVICE_NAME:latest)
    
    # Wait for health check
    while ! podman exec $container_id /usr/local/bin/health-check.sh 2>/dev/null; do
      sleep 0.1
    done
    
    end_time=$(date +%s.%N)
    startup_time=$(echo "$end_time - $start_time" | bc)
    startup_times+=($startup_time)
    
    podman stop $container_id >/dev/null
    echo "Startup test $i: ${startup_time}s"
  done
  
  # Calculate average startup time
  avg_startup=$(echo "${startup_times[@]}" | awk '{for(i=1;i<=NF;i++) sum+=$i; print sum/NF}')
  echo "Average startup time: ${avg_startup}s"
  
  echo "✅ Performance testing completed"
}

validate_integration() {
  echo "=== Phase 5: Integration Testing ==="
  
  if [ -f "tests/integration/test-$SERVICE_NAME-integration.sh" ]; then
    bash tests/integration/test-$SERVICE_NAME-integration.sh
  else
    echo "⚠️  No integration test found for $SERVICE_NAME"
  fi
}

# Main validation logic
case $PHASE in
  isolation|2)
    validate_isolation
    ;;
  performance|3)
    validate_performance
    ;;
  integration|5)
    validate_integration
    ;;
  all)
    validate_isolation && validate_performance && validate_integration
    ;;
  *)
    echo "Usage: $0 <service-name> [isolation|performance|integration|all]"
    exit 1
    ;;
esac
```

## 🐛 Common Integration Issues and Solutions

### Issue: Service A can't communicate with Service B

**Symptoms**: Connection refused, timeout errors
**Debugging**:
```bash
# Check if services are in same pod
podman pod ps

# Check service is listening
podman exec serviceA netstat -tlnp

# Test connectivity
podman exec serviceA nc -zv localhost PORT
```

**Common Causes**:
- Services in different pods
- Wrong port number
- Service not fully started
- Firewall rules

### Issue: Services start in wrong order

**Symptoms**: Dependency errors during startup
**Solution**: Use init containers or readiness probes
```yaml
spec:
  containers:
  - name: dependent-service
    image: service:latest
    readinessProbe:
      exec:
        command: ["check-dependency.sh"]
```

### Issue: Shared volume permission conflicts

**Symptoms**: Permission denied errors
**Solution**: Use init container for permission setup
```yaml
spec:
  initContainers:
  - name: setup-permissions
    image: base:latest
    command: ["chown", "-R", "1000:1000", "/data"]
```

### Issue: Performance degradation with multiple services

**Symptoms**: Slower response times, higher CPU usage
**Debugging**:
```bash
# Monitor resource usage
podman pod stats podserve-test

# Check for resource contention
podman exec service iostat -x 1 5
```

**Solutions**:
- Resource limits in pod spec
- Optimize service configurations
- Consider service placement

## 📊 Performance Monitoring

### Key Metrics to Track
```bash
# Service-specific monitoring script
#!/bin/bash

SERVICE_NAME=$1

echo "=== $SERVICE_NAME Performance Metrics ==="

# Memory usage
echo "Memory Usage:"
podman exec $SERVICE_NAME cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable"

# CPU usage
echo "CPU Usage:"
podman exec $SERVICE_NAME top -bn1 | grep "Cpu(s)"

# Disk I/O
echo "Disk I/O:"
podman exec $SERVICE_NAME iostat -x 1 1

# Network connections
echo "Network Connections:"
podman exec $SERVICE_NAME netstat -an | grep LISTEN

# Service-specific metrics
case $SERVICE_NAME in
  apache)
    echo "Apache Status:"
    podman exec $SERVICE_NAME curl -s http://localhost/server-status?auto
    ;;
  mail)
    echo "Mail Queue:"
    podman exec $SERVICE_NAME postqueue -p | wc -l
    ;;
  dns)
    echo "DNS Query Test:"
    time podman exec $SERVICE_NAME dig @localhost google.com
    ;;
esac
```

## 🎯 Success Criteria Templates

### Service Isolation Success (Phase 2)
- [ ] Starts consistently (5/5 attempts succeed)
- [ ] Health checks pass reliably  
- [ ] Responds to SIGTERM within 10 seconds
- [ ] Logs show clean startup sequence
- [ ] No error messages in logs
- [ ] Configuration validation works

### Performance Success (Phase 3)
- [ ] Startup time < X seconds (define per service)
- [ ] Memory usage < X MB baseline
- [ ] Service response time < X ms
- [ ] No memory leaks over 1 hour run
- [ ] CPU usage < X% under normal load
- [ ] Graceful degradation under stress

### Integration Success (Phase 5)
- [ ] All service combinations tested
- [ ] Inter-service communication works
- [ ] No port or resource conflicts
- [ ] Combined startup time acceptable
- [ ] Health checks pass for all services
- [ ] Failure recovery works correctly

## 📚 Documentation Integration

This guide complements existing PodServe documentation:

- **[PRINCIPLES.md](PRINCIPLES.md)**: Follow core principles during each phase
- **[DEBUGGING-GUIDE.md](DEBUGGING-GUIDE.md)**: Use debugging techniques when validation fails
- **[PERMISSIONS-GUIDE.md](PERMISSIONS-GUIDE.md)**: Apply permission patterns during integration
- **[python-implementation-guide.md](../services-docs/python-implementation-guide.md)**: Reference implementation patterns

## 💡 Key Takeaways

1. **Isolation First**: Get each service rock-solid before combining
2. **Define Success**: Clear criteria prevent endless tweaking
3. **Measure Everything**: Performance baselines catch regressions
4. **Test Systematically**: Pairs, then triplets, then full integration
5. **Document as You Go**: Capture decisions and learnings immediately
6. **Validate at Gates**: Don't proceed until current phase is complete

Remember: Time spent validating individual services saves exponentially more time debugging complex integration issues later.