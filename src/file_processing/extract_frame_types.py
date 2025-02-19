import os
import pyshark
import argparse
import sys

QUIC_FRAME_TYPES = {
    "PADDING": 0,
    "PING": 1,
    "ACK": 2,
    "RESET_STREAM": 3,
    "STOP_SENDING": 5,
    "CRYPTO": 6,
    "NEW_TOKEN": 7,
    "STREAM": list(range(8, 16)),
    "MAX_DATA": 16,
    "MAX_STREAM_DATA": 17,
    "MAX_STREAMS_BIDI": 18,
    "MAX_STREAMS_UNI": 19,
    "DATA_BLOCKED": 20,
    "STREAM_DATA_BLOCKED": 21,
    "STREAMS_BLOCKED_BIDI": 22,
    "STREAMS_BLOCKED_UNI": 23,
    "NEW_CONNECTION_ID": 24,
    "RETIRE_CONNECTION_ID": 25,
    "PATH_CHALLENGE": 26,
    "PATH_RESPONSE": 27,
    "CONNECTION_CLOSE": 28,
    "APPLICATION_CLOSE": 29,
    "HANDSHAKE_DONE": 30,
}

def extract_quic_frame_types(packet):
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
            frame_types.update(QUIC_FRAME_TYPES["STREAM"])

        if hasattr(quic_layer, 'max_data'):
            frame_types.add(QUIC_FRAME_TYPES["MAX_DATA"])

        if hasattr(quic_layer, 'max_stream_data'):
            frame_types.add(QUIC_FRAME_TYPES["MAX_STREAM_DATA"])

        if hasattr(quic_layer, 'max_streams'):
            try:
                max_streams_type = int(quic_layer.max_streams_type)
                if max_streams_type == 0:
                    frame_types.add(QUIC_FRAME_TYPES["MAX_STREAMS_BIDI"])
                elif max_streams_type == 1:
                    frame_types.add(QUIC_FRAME_TYPES["MAX_STREAMS_UNI"])
            except ValueError:
                pass

        if hasattr(quic_layer, 'streams_blocked_type'):
            try:
                streams_blocked_type = int(quic_layer.streams_blocked_type)
                if streams_blocked_type == 0:
                    frame_types.add(QUIC_FRAME_TYPES["STREAMS_BLOCKED_BIDI"])
                elif streams_blocked_type == 1:
                    frame_types.add(QUIC_FRAME_TYPES["STREAMS_BLOCKED_UNI"])
            except ValueError:
                pass

        if hasattr(quic_layer, 'new_connection_id'):
            frame_types.add(QUIC_FRAME_TYPES["NEW_CONNECTION_ID"])

        if hasattr(quic_layer, 'retire_connection_id'):
            frame_types.add(QUIC_FRAME_TYPES["RETIRE_CONNECTION_ID"])

        if hasattr(quic_layer, 'path_challenge_data'):
            frame_types.add(QUIC_FRAME_TYPES["PATH_CHALLENGE"])

        if hasattr(quic_layer, 'path_response_data'):
            frame_types.add(QUIC_FRAME_TYPES["PATH_RESPONSE"])

        if hasattr(quic_layer, 'ping'):
            frame_types.add(QUIC_FRAME_TYPES["PING"])

        if hasattr(quic_layer, 'handshake_done'):
            frame_types.add(QUIC_FRAME_TYPES["HANDSHAKE_DONE"])

    return list(frame_types)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('case', type=str)
    parser.add_argument('--outfile', type=str, default=None, help='Output file path')
    args = parser.parse_args()

    if args.outfile:
        sys.stdout = open(args.outfile, 'w')

    def extract_pcap_name(pcap_path):
        file_name = os.path.basename(pcap_path)
        name_without_extension = os.path.splitext(file_name)[0]
        return name_without_extension

    base_dir = '/home/philipp/Documents/Thesis'
    case = extract_pcap_name(args.case)
    pcap_file = f'{base_dir}/packet_capture/{case}.pcap'
    keylog_file = f'{base_dir}/secrets_files/{case}.txt'

    def verify_decryption(pcap_file, keylog_file):
        cap = pyshark.FileCapture(
            pcap_file,
            override_prefs={
                'tls.keylog_file': keylog_file,
                'tls.desegment_ssl_records': 'TRUE',
                'tls.desegment_ssl_application_data': 'TRUE',
            },
        )

        decrypted_count = 0
        encrypted_count = 0
        quic_count = 0
        http3_count = 0

        for packet in cap:
            try:
                if hasattr(packet, 'quic'):
                    quic_count += 1
                    if hasattr(packet.quic, 'payload'):
                        decrypted_count += 1
                    else:
                        encrypted_count += 1
                if hasattr(packet, 'http3'):
                    http3_count += 1

            except AttributeError:
                encrypted_count += 1

        return decrypted_count, encrypted_count, quic_count, http3_count

    cap = pyshark.FileCapture(
        pcap_file,
        override_prefs={
            'tls.keylog_file': keylog_file,
            'tls.desegment_ssl_records': 'TRUE',
            'tls.desegment_ssl_application_data': 'TRUE',
        },
    )

    for packet in cap:
        print(f"Packet Number: {packet.number}")
        print(f"Source IP: {packet.ip.src}")
        print(f"Destination IP: {packet.ip.dst}")
        print(f"Packet Length: {packet.length}")
        print(f"Protocol: {packet.transport_layer}")
        print(f"Arrival Time: {packet.frame_info.time}")

        if hasattr(packet, 'quic'):
            for layer in packet.layers:
                if layer.layer_name == 'quic':
                    quic_frame_info = [
                        f"Connection number: {getattr(layer, 'connection_number', 'N/A')}",
                        f"Packet Length: {getattr(layer, 'packet_length', 'N/A')}",
                        f"Destination Connection ID: {getattr(layer, 'dcid', 'N/A')}",
                        f"Source Connection ID: {getattr(layer, 'scid', 'N/A')}" if hasattr(layer, 'scid') else "",
                        f"Packet number: {getattr(layer, 'packet_number', 'N/A')}",
                        f"Length: {getattr(layer, 'length', 'N/A')}",
                        f"Protected Payload: {getattr(layer, 'protected_payload', 'N/A')}" if hasattr(layer, 'protected_payload') else "",
                        f"Payload: {getattr(layer, 'payload', 'N/A')}" if hasattr(layer, 'payload') else "",
                        f"Frame Type: {getattr(layer, 'frame_type', 'N/A')}"
                    ]
                    quic_frames.append("\n".join(filter(None, quic_frame_info)))

        if hasattr(packet, 'http3'):
            for layer in packet.layers:
                if layer.layer_name == 'http3':
                    http3_frame_info = [
                        f"Frame Type: {getattr(layer, 'frame_type', 'N/A')}",
                        f"Frame Length: {getattr(layer, 'frame_length', 'N/A')}",
                        f"Frame Payload: {getattr(layer, 'frame_payload', 'N/A')}",
                        f"Settings Max Table Capacity: {getattr(layer, 'settings_qpack_max_table_capacity', 'N/A')}" if hasattr(layer, 'settings_qpack_max_table_capacity') else ""
                    ]
                    http3_frames.append("\n".join(filter(None, http3_frame_info)))

        if quic_frames:
            print("QUIC Frames Found:")
            print("\n\n".join(quic_frames))

        if http3_frames:
            print("HTTP3 Frames Found:")
            print("\n\n".join(http3_frames))

        print('-' * 50)

    pcap_name = extract_pcap_name(pcap_file)
    print(f"Extracted PCAP name: {pcap_name}")
    print(f"Test string: {case}")

    decrypted_count, encrypted_count, quic_count, http3_count = verify_decryption(pcap_file, keylog_file)
    print(f"Decrypted packets: {decrypted_count}")
    print(f"Encrypted packets: {encrypted_count}")
    print(f"QUIC packets: {quic_count}")
    print(f"HTTP3 packets: {http3_count}")

