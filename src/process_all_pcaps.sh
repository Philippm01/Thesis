#!/bin/bash

CAPTURE_DIR="/home/philipp/Documents/Thesis/packet_capture"
SCRIPT_PATH="/home/philipp/Documents/Thesis/src/pcap_to_json.py"

# Create results directory if it doesn't exist
mkdir -p "/home/philipp/Documents/Thesis/result_files"

# Process each pcap file
for pcap_file in "$CAPTURE_DIR"/*.pcap; do
    if [ -f "$pcap_file" ]; then
        filename=$(basename "$pcap_file")
        case_name="${filename%.*}" 
        echo "Processing $filename..."
        python3 "$SCRIPT_PATH" "$case_name"
    fi
done

echo "All pcap files have been processed!"
