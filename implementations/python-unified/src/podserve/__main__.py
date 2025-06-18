"""Main entry point for PodServe services."""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.service import ServiceRunner


def main():
    """Main entry point for PodServe services."""
    parser = argparse.ArgumentParser(description='PodServe Container Services')
    parser.add_argument('service', choices=['mail', 'apache', 'dns', 'certbot'],
                        help='Service to run')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Run the specified service
    runner = ServiceRunner()
    runner.run_service(args.service, debug=args.debug)


if __name__ == '__main__':
    main()