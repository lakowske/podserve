"""Main entry point for PodServe-Harmony services."""

import sys
import argparse
from typing import Dict, Type

from podserve.core.service import BaseService


def get_service_classes() -> Dict[str, Type[BaseService]]:
    """Get available service classes."""
    services = {}
    
    try:
        from podserve.services.certificates import CertificateService
        services['certificates'] = CertificateService
    except ImportError:
        pass
    
    try:
        from podserve.services.dns import DNSService
        services['dns'] = DNSService
    except ImportError:
        pass
    
    # Future services will be added here as they're implemented
    
    return services


def main():
    """Main entry point for services."""
    parser = argparse.ArgumentParser(description='PodServe-Harmony Services')
    parser.add_argument('service', help='Service to run', 
                       choices=list(get_service_classes().keys()))
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug logging')
    parser.add_argument('--mode', default='run',
                       help='Service mode (varies by service)')
    
    args = parser.parse_args()
    
    service_classes = get_service_classes()
    service_class = service_classes.get(args.service)
    
    if not service_class:
        print(f"Service '{args.service}' not found")
        sys.exit(1)
    
    try:
        service = service_class(debug=args.debug)
        
        # Handle service modes
        if hasattr(service, 'run_mode') and args.mode != 'run':
            success = service.run_mode(args.mode)
        else:
            success = service.run()
            
        if not success:
            print(f"Service '{args.service}' failed to start")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("Service interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Service error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()