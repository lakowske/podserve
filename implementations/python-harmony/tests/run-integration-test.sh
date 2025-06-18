#!/bin/bash
# Integration Test Runner for Certificate Service
# Tests certificate consumption patterns

set -e

INTEGRATION_TEST_DIR="./integration-test-data"
POD_NAME="certificate-integration-test"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INTEGRATION]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[INTEGRATION]${NC} $1"
}

log_error() {
    echo -e "${RED}[INTEGRATION]${NC} $1"
}

log_phase() {
    echo -e "${BLUE}[PHASE 4]${NC} $1"
}

# Cleanup function
cleanup() {
    log "Cleaning up integration test environment"
    podman pod rm -f "$POD_NAME" 2>/dev/null || true
    rm -rf "$INTEGRATION_TEST_DIR" 2>/dev/null || true
}

# Setup test environment
setup_test_env() {
    log "Setting up integration test environment"
    cleanup
    mkdir -p "$INTEGRATION_TEST_DIR"/{certificates,logs}
    chmod 755 "$INTEGRATION_TEST_DIR"/{certificates,logs}
}

# Run integration test
run_integration_test() {
    log_phase "Certificate Service Integration Test"
    
    log "Starting integration test pod..."
    
    # Run the pod with proper user namespace mapping
    if ! podman play kube --userns=keep-id tests/integration-certificate-consumer.yaml; then
        log_error "Failed to start integration test pod"
        return 1
    fi
    
    # Wait for initialization
    log "Waiting for certificate initialization..."
    sleep 10
    
    # Check init container status
    init_status=$(podman pod inspect "$POD_NAME" --format '{{range .Containers}}{{if eq .Name "certificate-integration-test-cert-init"}}{{.State}}{{end}}{{end}}' 2>/dev/null || echo "unknown")
    
    if [ "$init_status" != "exited" ]; then
        log_error "Certificate initialization failed"
        podman logs "$POD_NAME-cert-init" 2>/dev/null || true
        return 1
    fi
    
    log "Certificate initialization completed"
    
    # Monitor the test consumer
    log "Running certificate consumer integration test..."
    
    # Wait for test completion (up to 60 seconds)
    for i in $(seq 1 12); do
        consumer_status=$(podman pod inspect "$POD_NAME" --format '{{range .Containers}}{{if eq .Name "certificate-integration-test-cert-consumer"}}{{.State}}{{end}}{{end}}' 2>/dev/null || echo "unknown")
        
        if [ "$consumer_status" = "exited" ]; then
            # Check exit code
            consumer_logs=$(podman logs "$POD_NAME-cert-consumer" 2>/dev/null || echo "No logs available")
            
            if echo "$consumer_logs" | grep -q "Integration test completed successfully"; then
                log "✅ Integration test PASSED"
                echo ""
                echo "Integration test output:"
                echo "$consumer_logs"
                return 0
            else
                log_error "❌ Integration test FAILED"
                echo ""
                echo "Consumer logs:"
                echo "$consumer_logs"
                return 1
            fi
        fi
        
        log "Test running... [$i/12]"
        sleep 5
    done
    
    log_error "Integration test timed out"
    return 1
}

# Verify certificate files
verify_certificates() {
    log "Verifying certificate files on host"
    
    if [ -f "$INTEGRATION_TEST_DIR/certificates/cert.pem" ] && \
       [ -f "$INTEGRATION_TEST_DIR/certificates/privkey.pem" ] && \
       [ -f "$INTEGRATION_TEST_DIR/certificates/fullchain.pem" ]; then
        log "✅ Certificate files persisted to host volume"
        
        # Show certificate details
        echo ""
        echo "Certificate details:"
        openssl x509 -in "$INTEGRATION_TEST_DIR/certificates/cert.pem" -noout -text | head -15
        
        # Show file permissions
        echo ""
        echo "File permissions:"
        ls -la "$INTEGRATION_TEST_DIR/certificates/"
        
        return 0
    else
        log_error "❌ Certificate files not found on host"
        ls -la "$INTEGRATION_TEST_DIR/" 2>/dev/null || true
        return 1
    fi
}

# Generate integration test report
generate_report() {
    local test_result=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local report_file="integration-test-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# Certificate Service Integration Test Report

**Test Date**: $timestamp
**Test Type**: Phase 4 Integration Testing
**Pod Configuration**: integration-certificate-consumer.yaml

## Test Results

$(if [ $test_result -eq 0 ]; then
    echo "✅ **PASSED**: Certificate consumption pattern works correctly"
else
    echo "❌ **FAILED**: Integration test encountered errors"
fi)

## Test Scenarios Validated

- [$([ $test_result -eq 0 ] && echo "x" || echo " ")] Certificate file generation and persistence
- [$([ $test_result -eq 0 ] && echo "x" || echo " ")] Shared volume mount access
- [$([ $test_result -eq 0 ] && echo "x" || echo " ")] Certificate validity verification
- [$([ $test_result -eq 0 ] && echo "x" || echo " ")] File permission correctness
- [$([ $test_result -eq 0 ] && echo "x" || echo " ")] Consumer service certificate access

## Integration Pattern Verified

\`\`\`yaml
# Pattern: Certificate Producer + Consumer
initContainers:
- name: cert-init
  # Generates certificates in shared volume

containers:
- name: certificates
  # Runs certificate service in cron mode
  
- name: consumer
  # Reads certificates from shared volume (read-only)
\`\`\`

## Volume Mount Strategy

- **Host Path**: ./integration-test-data/certificates
- **Container Mount**: /data/state/certificates (producer), /test/ssl (consumer)
- **User Namespace**: --userns=keep-id for proper permissions
- **SELinux Context**: :Z for volume labels

## Phase 4 Status

$(if [ $test_result -eq 0 ]; then
    echo "✅ **Certificate service ready for production integration**"
    echo ""
    echo "**Next Steps**:"
    echo "1. Begin DNS service development (no certificate dependency)"
    echo "2. Plan Apache service integration (certificate consumer)"
    echo "3. Plan Mail service integration (certificate consumer)"
else
    echo "❌ **Integration issues need resolution before proceeding**"
    echo ""
    echo "**Required Actions**:"
    echo "1. Review integration test logs"
    echo "2. Fix certificate consumption patterns"
    echo "3. Re-run integration validation"
fi)

EOF

    log "Integration test report generated: $report_file"
}

# Main execution
main() {
    log_phase "Starting Certificate Service Integration Testing"
    
    # Check if certificate image exists
    if ! podman image exists "localhost/podserve-harmony-certificates:latest"; then
        log_error "Certificate service image not found. Please run: cd docker && ./build-dev.sh certificates"
        exit 1
    fi
    
    setup_test_env
    
    # Run the integration test
    if run_integration_test; then
        verify_certificates
        test_result=$?
    else
        test_result=1
    fi
    
    # Generate report
    generate_report $test_result
    
    # Cleanup
    cleanup
    
    # Final summary
    if [ $test_result -eq 0 ]; then
        log_phase "🎉 Phase 4 Integration Testing COMPLETED SUCCESSFULLY"
        echo ""
        echo "Certificate service integration patterns validated:"
        echo "✅ Shared volume certificate generation"
        echo "✅ Consumer access to certificates"
        echo "✅ Proper file permissions and security"
        echo "✅ Ready for downstream service integration"
        echo ""
        echo "Ready to proceed with next service development!"
        exit 0
    else
        log_error "Phase 4 Integration Testing FAILED"
        exit 1
    fi
}

# Handle interrupts
trap cleanup EXIT INT TERM

# Run main function
main "$@"