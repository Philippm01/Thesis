#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <filename>"
    exit 1
fi

FILENAME=$1
PCAP_FILE="./packet_capture/${FILENAME}"
KEY_FILE="./secrets_files/${FILENAME%.*}.txt"

if [ ! -f "$PCAP_FILE" ]; then
    echo "Error: PCAP file not found: $PCAP_FILE"
    exit 1
fi

if [ ! -f "$KEY_FILE" ]; then
    echo "Key log file not found: $KEY_FILE"
    exit 1
fi

tshark -r "$PCAP_FILE" -o "tls.keylog_file:$KEY_FILE" -V | head -n 1000