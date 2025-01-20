import os
import pyshark
import argparse

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
    quic_frames = []
    http3_frames = []

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
