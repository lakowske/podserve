# Service Development Checklist Template

Copy this template for each new service to ensure systematic development and validation.

## Service Information

**Service Name**: _________________
**Developer**: _________________
**Start Date**: _________________
**Target Completion**: _________________

## Phase 1: Service Planning and Design

### Service Scope Definition
- [ ] **Service Purpose**: What does this service do?
  - _________________________________________________________________
- [ ] **Ports/Protocols**: What ports and protocols does it use?
  - _________________________________________________________________
- [ ] **Data Persistence**: What data needs to persist?
  - _________________________________________________________________
- [ ] **Configuration**: What configuration is required?
  - _________________________________________________________________

### Health Check Strategy
- [ ] **Liveness Check**: How will we know the service is alive?
  - Command: ___________________________________________________
  - Timeout: ___________________________________________________
- [ ] **Readiness Check**: How will we know the service is ready?
  - Command: ___________________________________________________
  - Timeout: ___________________________________________________
- [ ] **Health Check Performance**: How long should checks take?
  - Target: < _______ seconds

### Performance Targets
- [ ] **Startup Time**: What's acceptable startup time?
  - Target: < _______ seconds
- [ ] **Memory Usage**: What's acceptable memory usage?
  - Target: < _______ MB
- [ ] **Response Time**: What response time targets exist?
  - Target: < _______ ms
- [ ] **Throughput**: What throughput is expected?
  - Target: > _______ requests/second

### Testing Strategy
- [ ] **Isolation Testing**: How will we test this service alone?
  - Test plan: _______________________________________________
- [ ] **Integration Points**: What integration points need testing?
  - Dependencies: ___________________________________________
- [ ] **Failure Modes**: What failure modes should we test?
  - Scenarios: ______________________________________________
- [ ] **Performance Benchmarks**: What performance tests will we run?
  - Benchmarks: ____________________________________________

### Dependencies and Integration
- [ ] **Service Dependencies**: What other services does this depend on?
  - Dependencies: ___________________________________________
- [ ] **Service Dependents**: What services will depend on this?
  - Dependents: _____________________________________________
- [ ] **Shared Resources**: What shared volumes/configs are needed?
  - Shared resources: _______________________________________
- [ ] **Network Communication**: What network communication is required?
  - Communication patterns: _________________________________

**Phase 1 Sign-off**: _________________ Date: _________________

## Phase 2: Isolated Service Development

### Container Implementation
- [ ] **Dockerfile**: Follows base image patterns
- [ ] **User Management**: Service runs as appropriate user
- [ ] **Signal Handling**: Proper signal handling implemented
- [ ] **Environment Variables**: Environment variable configuration complete

### Service Class Implementation (Python services)
- [ ] **Base Class**: Inherits from BaseService
- [ ] **Configure Method**: Implements configure() → bool
- [ ] **Start Processes**: Implements start_processes() → bool
- [ ] **Return Values**: Returns True/False correctly (not None!)
- [ ] **Logging**: Comprehensive logging with DEBUG level

### Health Check Implementation
- [ ] **Health Script**: Simple, fast health check commands
- [ ] **Liveness/Readiness**: Both liveness and readiness checks
- [ ] **Success Criteria**: Clear success/failure criteria
- [ ] **Error Reporting**: Proper error reporting

### Configuration Management
- [ ] **Template Rendering**: Template rendering works correctly
- [ ] **Environment Variables**: All required environment variables handled
- [ ] **Default Values**: Default values for development
- [ ] **Configuration Validation**: Configuration validation implemented

### Isolation Testing Results
```bash
# Test commands used:
# podman run --rm -e LOG_LEVEL=DEBUG localhost/podserve-SERVICE:latest SERVICE
# podman run --rm localhost/podserve-SERVICE:latest /usr/local/bin/health-check.sh

Test Date: _________________
```

- [ ] **Startup Success**: Service starts consistently (5/5 attempts)
- [ ] **Health Checks**: Health checks pass reliably
- [ ] **Configuration**: Configuration templates render correctly
- [ ] **Resource Usage**: Resource usage within targets
- [ ] **Clean Logs**: Logs show clean startup sequence
- [ ] **Signal Handling**: Service handles SIGTERM gracefully

**Phase 2 Sign-off**: _________________ Date: _________________

## Phase 3: Performance Baseline and Validation

### Performance Test Results

**Test Date**: _________________
**Image**: localhost/podserve-SERVICE:latest
**Environment**: Development (____GB RAM, ____ CPU)

#### Startup Time Test
```
Attempt 1: _______ seconds
Attempt 2: _______ seconds
Attempt 3: _______ seconds
Attempt 4: _______ seconds
Attempt 5: _______ seconds
Average: _______ seconds
```
- [ ] **Target Met**: < _____ seconds ✅/❌

#### Memory Usage Test
```
Baseline: _______ MB
After 10 minutes: _______ MB
After 1 hour: _______ MB
```
- [ ] **Target Met**: < _____ MB ✅/❌

#### Service Response Test
```
Response time: _______ ms
Throughput: _______ requests/sec
```
- [ ] **Response Target Met**: < _____ ms ✅/❌
- [ ] **Throughput Target Met**: > _____ requests/sec ✅/❌

### Issues Found and Resolved
1. **Issue**: ________________________________________________
   **Resolution**: __________________________________________

2. **Issue**: ________________________________________________
   **Resolution**: __________________________________________

### Performance Validation
- [ ] **All Targets Met**: All performance targets met or documented variance
- [ ] **No Memory Leaks**: No memory leaks during extended run (1 hour)
- [ ] **Restart Recovery**: Restart recovery time acceptable
- [ ] **Resource Stability**: Resource usage predictable and stable

**Phase 3 Sign-off**: _________________ Date: _________________

## Phase 4: Integration Planning

### Integration Strategy
- [ ] **Dependency Order**: Planned which service should start first
- [ ] **Communication Patterns**: Documented how services will interact
- [ ] **Shared Resources**: Identified what volumes/configs are shared
- [ ] **Failure Scenarios**: Planned what happens if this service fails

### Integration Test Combinations Planned
- [ ] **SERVICE + DNS**: _____________________________________
- [ ] **SERVICE + Apache**: __________________________________
- [ ] **SERVICE + Mail**: ____________________________________
- [ ] **SERVICE + ____________**: ____________________________
- [ ] **Full Integration**: ___________________________________

**Phase 4 Sign-off**: _________________ Date: _________________

## Phase 5: Service Combination and Testing

### Integration Test Results

#### Pair Testing
- [ ] **SERVICE + DNS**
  - Test Date: _________________
  - Result: ✅/❌
  - Issues: ________________________________________________

- [ ] **SERVICE + Apache**
  - Test Date: _________________
  - Result: ✅/❌
  - Issues: ________________________________________________

- [ ] **SERVICE + ____________**
  - Test Date: _________________
  - Result: ✅/❌
  - Issues: ________________________________________________

#### Integration Test Checklist (per combination)
- [ ] **Startup Order**: Services start in correct sequence
- [ ] **Health Checks**: All services report healthy
- [ ] **Communication**: Inter-service communication works
- [ ] **Shared Resources**: No volume/config conflicts
- [ ] **Performance**: Combined performance acceptable
- [ ] **Failure Recovery**: Services recover from restarts
- [ ] **Resource Usage**: Total resource usage within limits

### Full Integration Test
- [ ] **All Services**: Full pod with all services tested
  - Test Date: _________________
  - Result: ✅/❌
  - Performance impact: ___________________________________
  - Issues found: _____________________________________

**Phase 5 Sign-off**: _________________ Date: _________________

## Phase 6: Production Readiness

### Documentation Complete
- [ ] **Service Purpose**: Service purpose and functionality documented
- [ ] **Configuration**: Configuration options documented
- [ ] **Health Checks**: Health check endpoints documented
- [ ] **Troubleshooting**: Troubleshooting guide updated
- [ ] **Performance**: Performance characteristics documented

### Security Review
- [ ] **Minimal Privileges**: Runs with minimal required privileges
- [ ] **No Secrets**: No secrets in environment variables
- [ ] **File Permissions**: Proper file permissions
- [ ] **Network Security**: Network security validated

### Operational Readiness
- [ ] **Monitoring**: Monitoring/alerting configured
- [ ] **Log Levels**: Log levels appropriate for production
- [ ] **Backup/Restore**: Backup/restore procedures documented
- [ ] **Upgrade Procedures**: Upgrade procedures tested

### Integration Testing Complete
- [ ] **All Combinations**: All service combinations tested
- [ ] **Load Performance**: Performance under load validated
- [ ] **Failure Scenarios**: Failure scenarios tested
- [ ] **Recovery Procedures**: Recovery procedures validated

**Phase 6 Sign-off**: _________________ Date: _________________

## Final Service Sign-off

**Service Ready for Production**: ✅/❌

**Final Sign-off**: 
- Developer: _________________ Date: _________________
- Reviewer: _________________ Date: _________________

### Lessons Learned
1. _________________________________________________________________
2. _________________________________________________________________
3. _________________________________________________________________

### Recommendations for Future Services
1. _________________________________________________________________
2. _________________________________________________________________
3. _________________________________________________________________