#!/bin/bash


FILENAME=$1
PCAP_FILE="./packet_capture/${FILENAME}"
KEY_FILE="./secrets_files/${FILENAME%.*}.txt"

tshark -r "$PCAP_FILE" -o "tls.keylog_file:$KEY_FILE" -V | head -n 1000