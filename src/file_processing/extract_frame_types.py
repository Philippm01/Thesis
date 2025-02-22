import os
import pyshark
import argparse
import sys

QUIC_FRAME_TYPES = {
    "PADDING": 0x00,
    "PING": 0x01,
    "ACK": 0x02,
    "RESET_STREAM": 0x04,
    "STOP_SENDING": 0x05,
    "CRYPTO": 0x06,
    "NEW_TOKEN": 0x07,
    "STREAM": list(range(0x08, 0x10)),
    "MAX_DATA": 0x10,
    "MAX_STREAM_DATA": 0x11,
    "MAX_STREAMS_BIDI": 0x12,
    "MAX_STREAMS_UNI": 0x13,
    "DATA_BLOCKED": 0x14,
    "STREAM_DATA_BLOCKED": 0x15,
    "STREAMS_BLOCKED_BIDI": 0x16,
    "STREAMS_BLOCKED_UNI": 0x17,
    "NEW_CONNECTION_ID": 0x18,
    "RETIRE_CONNECTION_ID": 0x19,
    "PATH_CHALLENGE": 0x1A,
    "PATH_RESPONSE": 0x1B,
    "CONNECTION_CLOSE": 0x1C,
    "HANDSHAKE_DONE": 0x1E
}

unique_frame_types = set()

def extract_quic_frames(packet):
    frame_types = set()

    if hasattr(packet, 'quic'):
        quic_layer = packet.quic

        if hasattr(quic_layer, 'frame_type'):
            try:
                frame_type = int(quic_layer.frame_type)
                frame_types.add(frame_type)
            except ValueError:
                pass

        if hasattr(quic_layer, 'cc_error_code') and hasattr(quic_layer, 'cc_frame_type'):
            frame_types.add(QUIC_FRAME_TYPES["CONNECTION_CLOSE"])

        if hasattr(quic_layer, 'crypto_crypto_data'):
            frame_types.add(QUIC_FRAME_TYPES["CRYPTO"])

        if hasattr(quic_layer, 'ack_largest_acknowledged'):
            frame_types.add(QUIC_FRAME_TYPES["ACK"])

        if hasattr(quic_layer, 'stream_id') or hasattr(quic_layer, 'stream_data_length'):
            frame_types.add(QUIC_FRAME_TYPES["STREAM"][0])

        if hasattr(quic_layer, 'max_data'):
            frame_types.add(QUIC_FRAME_TYPES["MAX_DATA"])

        if hasattr(quic_layer, 'max_stream_data'):
            frame_types.add(QUIC_FRAME_TYPES["MAX_STREAM_DATA"])

        if hasattr(quic_layer, 'max_streams_bidi'):
            frame_types.add(QUIC_FRAME_TYPES["MAX_STREAMS_BIDI"])
        if hasattr(quic_layer, 'max_streams_uni'):
            frame_types.add(QUIC_FRAME_TYPES["MAX_STREAMS_UNI"])

        if hasattr(quic_layer, 'path_challenge_data'):
            frame_types.add(QUIC_FRAME_TYPES["PATH_CHALLENGE"])
        if hasattr(quic_layer, 'path_response_data'):
            frame_types.add(QUIC_FRAME_TYPES["PATH_RESPONSE"])

        if hasattr(quic_layer, 'ping'):
            frame_types.add(QUIC_FRAME_TYPES["PING"])

        if hasattr(quic_layer, 'handshake_done'):
            frame_types.add(QUIC_FRAME_TYPES["HANDSHAKE_DONE"])

    return list(frame_types)

def process_pcap(pcap_file, keylog_file):
    cap = pyshark.FileCapture(
        pcap_file,
        override_prefs={
            'tls.keylog_file': keylog_file,
            'tls.desegment_ssl_records': 'TRUE',
            'tls.desegment_ssl_application_data': 'TRUE',
        },
    )

    for packet in cap:
        try:
            if hasattr(packet, 'quic'):
                frame_types = extract_quic_frames(packet)
                for frame_type in frame_types:
                    unique_frame_types.add(frame_type)
        except AttributeError:
            pass

def extract_pcap_name(pcap_path):
    file_name = os.path.basename(pcap_path)
    return os.path.splitext(file_name)[0]

parser = argparse.ArgumentParser()
parser.add_argument('case', type=str)
parser.add_argument('--outfile', type=str, default=None, help='Output file path')
args = parser.parse_args()

if args.outfile:
    sys.stdout = open(args.outfile, 'w')

base_dir = '/home/philipp/Documents/Thesis'
case = extract_pcap_name(args.case)
pcap_file = f'{base_dir}/packet_capture/{case}.pcap'
keylog_file = f'{base_dir}/secrets_files/{case}.txt'

process_pcap(pcap_file, keylog_file)
