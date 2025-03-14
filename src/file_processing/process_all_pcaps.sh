#!/bin/bash

CAPTURE_DIR="/home/philipp/Documents/Thesis/packet_capture"
SCRIPT_PATH="/home/philipp/Documents/Thesis/src/file_processing/pcap_to_json.py"

mkdir -p "/home/philipp/Documents/Thesis/result_files"

for pcap_file in $(ls "$CAPTURE_DIR"/*.pcap | sort -V); do
    if [ -f "$pcap_file" ]; then
        filename=$(basename "$pcap_file")
        case_name="${filename%.*}" 
        echo "Processing $filename..."
        python3 "$SCRIPT_PATH" "$case_name"
    fi
done

echo "All pcap files have been processed!"