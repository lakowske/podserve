#!/bin/bash
# Automated validation script for Certificate Service - Phase 2 & 3 Testing
# Implements validation methodology from SERVICE-DEVELOPMENT-GUIDE.md

set -e

SERVICE_NAME="certificates"
IMAGE_NAME="localhost/podserve-harmony-certificates:latest"
TEST_DATA_DIR="./test-certificates-data"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Results tracking
TESTS_PASSED=0
TESTS_FAILED=0
PHASE_2_RESULTS=()
PHASE_3_RESULTS=()

log() {
    echo -e "${GREEN}[VALIDATE]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[VALIDATE]${NC} $1"
}

log_error() {
    echo -e "${RED}[VALIDATE]${NC} $1"
}

log_phase() {
    echo -e "${BLUE}[PHASE $1]${NC} $2"
}

# Test result tracking
pass_test() {
    local test_name="$1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    log "✅ PASS: $test_name"
}

fail_test() {
    local test_name="$1"
    local error="$2"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    log_error "❌ FAIL: $test_name - $error"
}

# Cleanup function
cleanup() {
    log "Cleaning up test environment"
    podman pod rm -f podserve-harmony-test 2>/dev/null || true
    podman rm -f certificates-test 2>/dev/null || true
    rm -rf "$TEST_DATA_DIR" 2>/dev/null || true
}

# Setup test environment
setup_test_env() {
    log "Setting up test environment"
    cleanup
    mkdir -p "$TEST_DATA_DIR"/{certificates,config,logs}
    chmod 755 "$TEST_DATA_DIR"/{certificates,config,logs}
}

# Phase 2: Isolation Testing
validate_isolation() {
    log_phase "2" "Isolation Testing"
    
    # Test 1: Basic service startup with persistent volumes
    log "Testing basic service startup with volume persistence..."
    if timeout 30 podman run --rm --userns=keep-id \
        -v "$TEST_DATA_DIR/certificates:/data/state/certificates:Z" \
        -v "$TEST_DATA_DIR/config:/data/config/certificates:Z" \
        -e LOG_LEVEL=DEBUG \
        "$IMAGE_NAME" \
        python3 -m podserve certificates --debug --mode init >/dev/null 2>&1; then
        pass_test "Service startup"
        PHASE_2_RESULTS+=("startup:PASS")
    else
        fail_test "Service startup" "Service failed to start within 30 seconds"
        PHASE_2_RESULTS+=("startup:FAIL")
        return 1
    fi
    
    # Test 2: Certificate generation (verify persistent files)
    log "Testing certificate generation..."
    if [ -f "$TEST_DATA_DIR/certificates/cert.pem" ] && \
       [ -f "$TEST_DATA_DIR/certificates/privkey.pem" ] && \
       [ -f "$TEST_DATA_DIR/certificates/fullchain.pem" ]; then
        pass_test "Certificate file generation"
        PHASE_2_RESULTS+=("cert_generation:PASS")
    else
        fail_test "Certificate file generation" "Required certificate files not created in persistent volume"
        PHASE_2_RESULTS+=("cert_generation:FAIL")
    fi
    
    # Test 3: Certificate validity
    log "Testing certificate validity..."
    if openssl x509 -in "$TEST_DATA_DIR/certificates/cert.pem" -noout -text >/dev/null 2>&1; then
        pass_test "Certificate validity"
        PHASE_2_RESULTS+=("cert_validity:PASS")
    else
        fail_test "Certificate validity" "Generated certificate is not valid"
        PHASE_2_RESULTS+=("cert_validity:FAIL")
    fi
    
    # Test 4: Health check
    log "Testing health check..."
    if podman run --rm --userns=keep-id \
        -v "$TEST_DATA_DIR/certificates:/data/state/certificates:Z" \
        "$IMAGE_NAME" \
        /usr/local/bin/health-check.sh certificates >/dev/null 2>&1; then
        pass_test "Health check"
        PHASE_2_RESULTS+=("health_check:PASS")
    else
        fail_test "Health check" "Health check command failed"
        PHASE_2_RESULTS+=("health_check:FAIL")
    fi
    
    # Test 5: Certificate validation (Python)
    log "Testing Python certificate validation..."
    if podman run --rm --userns=keep-id \
        -v "$TEST_DATA_DIR/certificates:/data/state/certificates:Z" \
        "$IMAGE_NAME" \
        python3 -c "
from podserve.services.certificates import CertificateService
import sys
try:
    service = CertificateService(debug=True)
    if service.health_check():
        print('Certificate validation passed')
        sys.exit(0)
    else:
        sys.exit(1)
except Exception as e:
    print(f'Validation error: {e}')
    sys.exit(1)
" >/dev/null 2>&1; then
        pass_test "Python certificate validation"
        PHASE_2_RESULTS+=("python_validation:PASS")
    else
        fail_test "Python certificate validation" "Python health check failed"
        PHASE_2_RESULTS+=("python_validation:FAIL")
    fi
    
    # Test 6: File permissions
    log "Testing file permissions..."
    cert_perms=$(stat -c "%a" "$TEST_DATA_DIR/certificates/cert.pem" 2>/dev/null || echo "000")
    key_perms=$(stat -c "%a" "$TEST_DATA_DIR/certificates/privkey.pem" 2>/dev/null || echo "000")
    
    if [ "$cert_perms" = "644" ] && [ "$key_perms" = "640" ]; then
        pass_test "File permissions"
        PHASE_2_RESULTS+=("permissions:PASS")
    else
        fail_test "File permissions" "Incorrect permissions: cert=$cert_perms (should be 644), key=$key_perms (should be 640)"
        PHASE_2_RESULTS+=("permissions:FAIL")
    fi
}

# Phase 3: Performance Testing
validate_performance() {
    log_phase "3" "Performance Baseline and Validation"
    
    # Test 1: Startup time measurement
    log "Measuring startup time..."
    startup_times=()
    for i in {1..3}; do
        start_time=$(date +%s.%N)
        
        if timeout 60 podman run --rm \
            "$IMAGE_NAME" \
            python3 -m podserve certificates --debug --mode init >/dev/null 2>&1; then
            
            end_time=$(date +%s.%N)
            startup_time=$(echo "$end_time - $start_time" | bc)
            startup_times+=($startup_time)
            log "Startup test $i: ${startup_time}s"
        else
            fail_test "Startup time test $i" "Service failed to start"
            PHASE_3_RESULTS+=("startup_time:FAIL")
            return 1
        fi
    done
    
    # Calculate average startup time
    avg_startup=$(echo "${startup_times[@]}" | awk '{for(i=1;i<=NF;i++) sum+=$i; print sum/NF}')
    log "Average startup time: ${avg_startup}s"
    
    # Check against target (10 seconds for self-signed)
    if (( $(echo "$avg_startup < 10" | bc -l) )); then
        pass_test "Startup time target (<10s)"
        PHASE_3_RESULTS+=("startup_time:PASS:${avg_startup}s")
    else
        fail_test "Startup time target" "Average startup time ${avg_startup}s exceeds 10s target"
        PHASE_3_RESULTS+=("startup_time:FAIL:${avg_startup}s")
    fi
    
    # Test 2: Memory usage
    log "Measuring memory usage..."
    container_id=$(podman run -d \
        "$IMAGE_NAME" \
        sleep 60)
    
    # Let it settle
    sleep 5
    
    # Get memory usage
    memory_usage=$(podman stats --no-stream --format "{{.MemUsage}}" "$container_id" | awk '{print $1}' | sed 's/MiB//')
    podman stop "$container_id" >/dev/null 2>&1
    podman rm "$container_id" >/dev/null 2>&1
    
    log "Memory usage: ${memory_usage}MB"
    
    # Check against target (50MB)
    if (( $(echo "$memory_usage < 50" | bc -l) )); then
        pass_test "Memory usage target (<50MB)"
        PHASE_3_RESULTS+=("memory_usage:PASS:${memory_usage}MB")
    else
        fail_test "Memory usage target" "Memory usage ${memory_usage}MB exceeds 50MB target"
        PHASE_3_RESULTS+=("memory_usage:FAIL:${memory_usage}MB")
    fi
    
    # Test 3: Certificate generation performance
    log "Measuring certificate generation performance..."
    gen_start=$(date +%s.%N)
    
    if podman run --rm \
        "$IMAGE_NAME" \
        python3 -c "
from podserve.services.certificates import CertificateService
service = CertificateService(debug=False)
service.configure()
service._create_self_signed()
" >/dev/null 2>&1; then
        
        gen_end=$(date +%s.%N)
        gen_time=$(echo "$gen_end - $gen_start" | bc)
        log "Certificate generation time: ${gen_time}s"
        
        # Check against target (5 seconds)
        if (( $(echo "$gen_time < 5" | bc -l) )); then
            pass_test "Certificate generation time (<5s)"
            PHASE_3_RESULTS+=("generation_time:PASS:${gen_time}s")
        else
            fail_test "Certificate generation time" "Generation time ${gen_time}s exceeds 5s target"
            PHASE_3_RESULTS+=("generation_time:FAIL:${gen_time}s")
        fi
    else
        fail_test "Certificate generation performance test" "Generation failed"
        PHASE_3_RESULTS+=("generation_time:FAIL")
    fi
}

# Generate test report
generate_report() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local report_file="certificates-validation-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# Certificate Service Validation Report

**Test Date**: $timestamp
**Image**: $IMAGE_NAME
**Environment**: Development

## Summary
- **Tests Passed**: $TESTS_PASSED
- **Tests Failed**: $TESTS_FAILED
- **Success Rate**: $(( TESTS_PASSED * 100 / (TESTS_PASSED + TESTS_FAILED) ))%

## Phase 2: Isolation Testing Results
EOF

    for result in "${PHASE_2_RESULTS[@]}"; do
        local test_name=$(echo "$result" | cut -d: -f1)
        local test_result=$(echo "$result" | cut -d: -f2)
        echo "- **$test_name**: $test_result" >> "$report_file"
    done

    cat >> "$report_file" << EOF

## Phase 3: Performance Testing Results
EOF

    for result in "${PHASE_3_RESULTS[@]}"; do
        local test_name=$(echo "$result" | cut -d: -f1)
        local test_result=$(echo "$result" | cut -d: -f2)
        local test_value=$(echo "$result" | cut -d: -f3)
        if [ -n "$test_value" ]; then
            echo "- **$test_name**: $test_result ($test_value)" >> "$report_file"
        else
            echo "- **$test_name**: $test_result" >> "$report_file"
        fi
    done

    cat >> "$report_file" << EOF

## Recommendations
$(if [ $TESTS_FAILED -eq 0 ]; then
    echo "✅ Certificate service is ready for Phase 4: Integration Planning"
else
    echo "❌ Certificate service needs fixes before proceeding to Phase 4"
    echo "- Review failed tests above"
    echo "- Check logs in $TEST_DATA_DIR/logs"
    echo "- Verify container image build"
fi)

## Next Steps
- [ ] Complete Phase 4: Integration Planning
- [ ] Test certificate consumption by other services
- [ ] Validate certificate renewal processes
EOF

    log "Validation report generated: $report_file"
}

# Main execution
main() {
    log "Starting Certificate Service Validation"
    log "Following SERVICE-DEVELOPMENT-GUIDE.md Phase 2 & 3 validation"
    
    # Check if image exists
    if ! podman image exists "$IMAGE_NAME"; then
        log_error "Image $IMAGE_NAME not found. Please run: cd docker && ./build-dev.sh certificates"
        exit 1
    fi
    
    setup_test_env
    
    # Run Phase 2 validation
    if validate_isolation; then
        log_phase "2" "Isolation testing completed successfully"
    else
        log_error "Phase 2 isolation testing failed"
        cleanup
        generate_report
        exit 1
    fi
    
    # Run Phase 3 validation
    validate_performance
    
    # Generate report
    generate_report
    
    # Cleanup
    cleanup
    
    # Final summary
    if [ $TESTS_FAILED -eq 0 ]; then
        log "🎉 All tests passed! Certificate service is ready for Phase 4."
        echo ""
        echo "Next steps:"
        echo "1. Update CERTIFICATES-SERVICE-CHECKLIST.md with Phase 2 & 3 results"
        echo "2. Begin Phase 4: Integration Planning"
        echo "3. Design certificate consumption patterns for other services"
        exit 0
    else
        log_error "Some tests failed. Please review the report and fix issues before proceeding."
        exit 1
    fi
}

# Handle interrupts
trap cleanup EXIT INT TERM

# Run main function
main "$@"