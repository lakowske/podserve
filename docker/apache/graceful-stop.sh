#!/bin/bash
# Direct Apache shutdown script
# Since Apache is now PID 1, signals will be handled directly

echo "Initiating Apache shutdown..."

# Send SIGUSR1 to PID 1 (Apache) for graceful shutdown
echo "Sending graceful stop signal to Apache..."
kill -USR1 1

echo "Apache shutdown signal sent"