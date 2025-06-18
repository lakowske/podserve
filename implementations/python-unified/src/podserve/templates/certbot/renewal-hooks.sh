#!/bin/bash
#
# Certbot Renewal Hooks for PodServe
#
# This script contains hooks that run before, during, and after certificate renewal
#

# Pre-hook: Run before attempting renewal
pre_hook() {
    echo "$(date): Starting certificate renewal process"
    
    # Stop web server if needed for standalone authenticator
    # systemctl stop apache2 || true
    
    # Clear any existing challenge files
    rm -rf /var/www/html/.well-known/acme-challenge/*
    
    # Ensure webroot directory exists and has proper permissions
    mkdir -p /var/www/html/.well-known/acme-challenge
    chmod 755 /var/www/html/.well-known/acme-challenge
    chown www-data:www-data /var/www/html/.well-known/acme-challenge 2>/dev/null || true
}

# Post-hook: Run after successful renewal
post_hook() {
    echo "$(date): Certificate renewal completed successfully"
    
    # Copy certificates to application directory
    if [ -d "/etc/letsencrypt/live" ]; then
        for domain_dir in /etc/letsencrypt/live/*/; do
            if [ -d "$domain_dir" ]; then
                domain=$(basename "$domain_dir")
                dest_dir="/data/state/certificates/$domain"
                
                echo "Copying certificates for $domain"
                mkdir -p "$dest_dir"
                
                # Copy certificate files
                if [ -f "$domain_dir/privkey.pem" ]; then
                    cp "$domain_dir/privkey.pem" "$dest_dir/privkey.pem"
                    chmod 600 "$dest_dir/privkey.pem"
                fi
                
                if [ -f "$domain_dir/fullchain.pem" ]; then
                    cp "$domain_dir/fullchain.pem" "$dest_dir/fullchain.pem"
                    chmod 644 "$dest_dir/fullchain.pem"
                fi
                
                if [ -f "$domain_dir/cert.pem" ]; then
                    cp "$domain_dir/cert.pem" "$dest_dir/cert.pem"
                    chmod 644 "$dest_dir/cert.pem"
                fi
                
                if [ -f "$domain_dir/chain.pem" ]; then
                    cp "$domain_dir/chain.pem" "$dest_dir/chain.pem"
                    chmod 644 "$dest_dir/chain.pem"
                fi
            fi
        done
    fi
    
    # Reload web server to use new certificates
    # systemctl reload apache2 || true
    
    # Send notification if desired
    # echo "Certificate renewed for domains: $(certbot certificates --quiet | grep 'Certificate Name' | cut -d' ' -f3)" | mail -s "SSL Certificate Renewed" admin@localhost
}

# Deploy-hook: Run once for each successfully renewed certificate
deploy_hook() {
    local renewed_domains="$RENEWED_DOMAINS"
    local renewed_lineage="$RENEWED_LINEAGE"
    
    echo "$(date): Deploying renewed certificate for domains: $renewed_domains"
    echo "$(date): Certificate lineage: $renewed_lineage"
    
    # Extract domain name from lineage path
    domain=$(basename "$renewed_lineage")
    
    # Update application configuration if needed
    # This could trigger a configuration reload for services using the certificate
    
    echo "$(date): Certificate deployment completed for $domain"
}

# Error handling
handle_error() {
    echo "$(date): Certificate renewal failed with error code $1"
    
    # Send alert notification
    # echo "Certificate renewal failed for $(hostname)" | mail -s "SSL Certificate Renewal Failed" admin@localhost
    
    # Log the error
    logger "Certbot renewal failed with exit code $1"
}

# Main execution based on script arguments
case "${1:-}" in
    "pre")
        pre_hook
        ;;
    "post")
        post_hook
        ;;
    "deploy")
        deploy_hook
        ;;
    "error")
        handle_error "${2:-1}"
        ;;
    *)
        echo "Usage: $0 {pre|post|deploy|error [exit_code]}"
        echo "This script is typically called by Certbot hooks"
        exit 1
        ;;
esac