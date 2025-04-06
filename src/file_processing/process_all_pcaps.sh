#!/bin/bash

CAPTURE_DIR="/home/philipp/Documents/Thesis/packet_capture"
SCRIPT_PATH="/home/philipp/Documents/Thesis/src/file_processing/pcap_to_json.py"

mkdir -p "/home/philipp/Documents/Thesis/result_files"

PREFIXES=("slowloris_isolated_con:5-10_sleep:1-5_time:100_it:" "quicly_isolation_time:100_it:" "lsquic_isolation_time:100_it:" "normal")

for pcap_file in $(ls "$CAPTURE_DIR"/*.pcap | sort -V); do
    if [ -f "$pcap_file" ]; then
        filename=$(basename "$pcap_file")
        case_name="${filename%.*}"
        for prefix in "${PREFIXES[@]}"; do
            if [[ "$filename" == "$prefix"* ]]; then
                echo "Processing $filename..."
                python3 "$SCRIPT_PATH" "$case_name"
                break
            fi
        done
    fi
done