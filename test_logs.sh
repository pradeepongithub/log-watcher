#!/bin/bash
# Generate test logs
echo "Generating logs to sample.log (Ctrl+C to stop)"
while true; do
    echo "[$(date +%H:%M:%S)] [$(shuf -e INFO DEBUG WARN ERROR -n1)] Request id=$RANDOM" >> sample.log
    sleep 1
done