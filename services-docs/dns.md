# DNS Service Configuration

## Key Components

**Base Image**: localhost/podserve-base:latest  
**Service**: BIND9 DNS forwarder  
**Exposed Ports**: 53 (UDP/TCP)

## Environment Variables

- `DNS_FORWARDERS`: Upstream DNS servers semicolon-separated (default: "8.8.8.8;8.8.4.4")
- `DNSSEC_ENABLED`: Enable DNSSEC validation (default: "no")

## Features

1. **DNS Forwarding**: Forwards queries to configured upstream servers
2. **Caching**: Local DNS cache to improve performance
3. **Configuration Template**: Uses envsubst for dynamic configuration

## Startup Process

1. Formats DNS forwarders for BIND configuration syntax
2. Processes configuration template with environment variables
3. Validates BIND configuration with named-checkconf
4. Starts BIND in foreground mode as bind user

## Health Check

Verifies DNS resolution by querying google.com A record via localhost

## Usage

This container acts as a caching DNS forwarder, useful for local development or as an internal DNS resolver that can be customized with specific upstream servers.