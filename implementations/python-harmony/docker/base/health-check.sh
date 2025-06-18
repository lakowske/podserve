#!/bin/bash
# Generic health check script for PodServe-Harmony services

set -e

SERVICE_NAME=${1:-certificates}

# Basic health check function
check_service_health() {
    local service=$1
    
    case $service in
        certificates)
            # Check if certificate files exist and are valid
            if [ ! -f "/data/state/certificates/cert.pem" ]; then
                echo "Certificate file not found"
                return 1
            fi
            
            # Check certificate validity (not expired)
            if ! openssl x509 -in /data/state/certificates/cert.pem -noout -checkend 86400 2>/dev/null; then
                echo "Certificate is expired or invalid"
                return 1
            fi
            
            # Use Python health check if available
            if command -v python3 >/dev/null 2>&1; then
                python3 -c "
from podserve.services.certificates import CertificateService
import sys
try:
    service = CertificateService()
    if service.health_check():
        print('Certificate service health check passed')
        sys.exit(0)
    else:
        print('Certificate service health check failed')
        sys.exit(1)
except Exception as e:
    print(f'Health check error: {e}')
    sys.exit(1)
" 2>/dev/null
            else
                echo "Certificate files present and valid"
                return 0
            fi
            ;;
        *)
            echo "Unknown service: $service"
            return 1
            ;;
    esac
}

# Run health check
if check_service_health "$SERVICE_NAME"; then
    echo "Health check passed for $SERVICE_NAME"
    exit 0
else
    echo "Health check failed for $SERVICE_NAME"
    exit 1
fi