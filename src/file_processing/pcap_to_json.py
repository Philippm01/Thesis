import os
import pyshark
import argparse
import json

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

def extract_quic_frames(packet):
    frame_types = set()

    if hasattr(packet, 'quic'):
        quic_layer = packet.quic

        if hasattr(quic_layer, 'frame_type'):
            try:
                frame_type = int(quic_layer.frame_type)
                frame_types.add(frame_type)
                if frame_type == QUIC_FRAME_TYPES["PING"]:
                    frame_types.add(QUIC_FRAME_TYPES["PING"])
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

def determine_attack_type(quic_frames, http3_frames, file_name):
    for frame in quic_frames:
        if frame == QUIC_FRAME_TYPES["CONNECTION_CLOSE"] and QUIC_FRAME_TYPES["CRYPTO"] in quic_frames:
            return 1
    for frame in http3_frames:
        try:
            if int(frame.get("Settings Max Table Capacity", 0)) >= 4096:
                return 2
        except (ValueError, TypeError):
            continue
    if QUIC_FRAME_TYPES["PING"] in quic_frames and "slowloris" in file_name:
        return 3
    return 0

parser = argparse.ArgumentParser()
parser.add_argument('case', type=str)
args = parser.parse_args()

def extract_pcap_name(pcap_path):
    file_name = os.path.basename(pcap_path)
    name_without_extension = os.path.splitext(file_name)[0]
    return name_without_extension

base_dir = '/home/philipp/Documents/Thesis'
case = extract_pcap_name(args.case)
pcap_file = f'{base_dir}/packet_capture/{case}.pcap'
keylog_file = f'{base_dir}/secrets_files/{case}.txt'

try:
    cap = pyshark.FileCapture(
        pcap_file,
        override_prefs={
            'tls.keylog_file': keylog_file,
            'tls.desegment_ssl_records': 'TRUE',
            'tls.desegment_ssl_application_data': 'TRUE',
        },
    )
    packets_info = []

    def print_packet_attributes(packet):
        print("\n=== NEW PACKET ===")
        print(f"Packet number: {packet.number}")
        if hasattr(packet, 'quic'):
            print("\nQUIC Layer Attributes:")
            for field_name in packet.quic.field_names:
                print(f"{field_name}: {getattr(packet.quic, field_name)}")
                
        if hasattr(packet, 'http3'):
            print("\nHTTP3 Layer Attributes:")
            for field_name in packet.http3.field_names:
                print(f"{field_name}: {getattr(packet.http3, field_name)}")

    for packet in cap:
        packet_info = {
            "Packet Number": packet.number,
            "Source IP": packet.ip.src,
            "Destination IP": packet.ip.dst,
            "Packet Length": packet.length,
            "Protocol": packet.transport_layer,
            "Arrival Time": packet.frame_info.time,
            "QUIC Frames": [],
            "HTTP3 Frames": []
        }

        if hasattr(packet, 'quic'):
            frame_types = extract_quic_frames(packet)
            for layer in packet.layers:
                if layer.layer_name == 'quic':
                    quic_packet_info = {
                        "Packet Length": getattr(layer, 'packet_length', 'N/A'),
                        "Destination Connection ID": getattr(layer, 'dcid', 'N/A'),
                        "Source Connection ID": getattr(layer, 'scid', 'N/A') if hasattr(layer, 'scid') else "",
                        "Packet number": getattr(layer, 'packet_number', 'N/A'),
                        "Length": getattr(layer, 'length', 'N/A'),
                        "Frame Types": frame_types
                    }
                    packet_info["QUIC Frames"].append(quic_packet_info)

        if hasattr(packet, 'http3'):
            for layer in packet.layers:
                if layer.layer_name == 'http3':
                    http3_packet_info = {
                        "Frame Type": getattr(layer, 'frame_type', 'N/A'),
                        "Frame Length": getattr(layer, 'frame_length', 'N/A'),
                        "Settings Max Table Capacity": getattr(layer, 'settings_qpack_max_table_capacity', 'N/A') if hasattr(layer, 'settings_qpack_max_table_capacity') else ""
                    }
                    packet_info["HTTP3 Frames"].append(http3_packet_info)

        attack_type = determine_attack_type(frame_types, packet_info["HTTP3 Frames"], case)
        packet_info["Attack Type"] = str(attack_type)  # Convert attack_type to string for JSON consistency

        packets_info.append(packet_info)

    cap.close()

except pyshark.capture.capture.TSharkCrashException as e:
    print(f"TShark crashed while processing {pcap_file}: {e}")
    print("Skipping this file due to incomplete or corrupted data.")

if packets_info:
    output_file = f'{base_dir}/result_files/{case}.json'
    with open(output_file, 'w') as f:
        json.dump(packets_info, f, indent=4)
    print(f"Results saved to {output_file}")
else:
    print(f"No valid packets processed for {pcap_file}.")


