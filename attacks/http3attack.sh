#!/bin/bash

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <concurrent_connections> <iterations> <url>"
    exit 1
fi

concurrent_connections=$1
iterations=$2
url=$3

trap "echo 'Interrupted'; exit" SIGINT

for i in $(seq 1 $iterations); do
    echo "Iteration $i"
    for j in $(seq 1 $concurrent_connections); do
        (python3 examples/http3_client.py --zero-rtt --insecure $url) &
    done
    wait
done
