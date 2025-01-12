#!/bin/bash

trap "kill 0" SIGINT


if [ "$#" -ne 6 ]; then
    echo "Usage: $0 <min_concurrent_connections> <max_concurrent_connections> <runtime_in_seconds> <min_loop_pause_seconds> <max_loop_pause_seconds> <url>"
    exit 1
fi

MIN_CONCURRENT_CONNECTIONS=$1
MAX_CONCURRENT_CONNECTIONS=$2
RUNTIME=$3
MIN_SLEEP_INTERVAL=$4
MAX_SLEEP_INTERVAL=$5
URL=$6 # https://192.168.0.103:4000/index.html

# Generate random values within the specified ranges
CONCURRENT_CONNECTIONS=$((RANDOM % (MAX_CONCURRENT_CONNECTIONS - MIN_CONCURRENT_CONNECTIONS + 1) + MIN_CONCURRENT_CONNECTIONS))
SLEEP_INTERVAL=$((RANDOM % (MAX_SLEEP_INTERVAL - MIN_SLEEP_INTERVAL + 1) + MIN_SLEEP_INTERVAL))

START_TIME=$(date +%s)

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED_TIME=$((CURRENT_TIME - START_TIME))
    REMAINING_TIME=$((RUNTIME - ELAPSED_TIME))

    if [ "$REMAINING_TIME" -le 0 ]; then
        echo "Finished"
        exit 0
    fi

    seq 1 "$CONCURRENT_CONNECTIONS" | xargs -n1 -P"$CONCURRENT_CONNECTIONS" bash -c \
        "timeout $REMAINING_TIME python3 examples/http3_client.py --zero-rtt --insecure $URL > /dev/null 2>&1 &"

    sleep "$SLEEP_INTERVAL"
done

