# Base Service Configuration

## Key Components

**Base Image**: debian:12-slim  
**Purpose**: Common base image for all PodServe services

## Pre-installed Packages

- **Basic utilities**: curl, wget, ca-certificates
- **Network tools**: net-tools, iproute2, ping, dig
- **Python**: python3, pip, venv, common libraries (yaml, jinja2, requests, cryptography)
- **SSL/Security**: openssl, ssl-cert
- **Text processing**: gettext-base, sed, gawk
- **Process management**: procps, psmisc

## Default Configuration

- **User**: Creates podserve user (UID/GID 1000)
- **Timezone**: UTC (configurable via TZ environment variable)
- **Directories**: Creates /data/config, /data/logs, /data/state
- **Python**: PEP 668 compliant package installation via apt

## Volume Mounts

- `/data/config`: Configuration files
- `/data/logs`: Application logs
- `/data/state`: Persistent state data

## Usage

This is a base image that other services extend. It provides common dependencies and directory structure to reduce duplication across service containers.