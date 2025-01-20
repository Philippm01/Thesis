import os
import pyshark
import argparse
import json

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

cap = pyshark.FileCapture(
    pcap_file,
    override_prefs={
        'tls.keylog_file': keylog_file,
        'tls.desegment_ssl_records': 'TRUE',
        'tls.desegment_ssl_application_data': 'TRUE',
    },
)
packets_info = []

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
        for layer in packet.layers:
            if layer.layer_name == 'quic':
                quic_frame_info = {
                    "Connection number": getattr(layer, 'connection_number', 'N/A'),
                    "Packet Length": getattr(layer, 'packet_length', 'N/A'),
                    "Destination Connection ID": getattr(layer, 'dcid', 'N/A'),
                    "Source Connection ID": getattr(layer, 'scid', 'N/A') if hasattr(layer, 'scid') else "",
                    "Packet number": getattr(layer, 'packet_number', 'N/A'),
                    "Length": getattr(layer, 'length', 'N/A'),
                    "Protected Payload": getattr(layer, 'protected_payload', 'N/A') if hasattr(layer, 'protected_payload') else "",
                    "Payload": getattr(layer, 'payload', 'N/A') if hasattr(layer, 'payload') else "",
                    "Frame Type": getattr(layer, 'frame_type', 'N/A')
                }
                packet_info["QUIC Frames"].append(quic_frame_info)

    if hasattr(packet, 'http3'):
        for layer in packet.layers:
            if layer.layer_name == 'http3':
                http3_frame_info = {
                    "Frame Type": getattr(layer, 'frame_type', 'N/A'),
                    "Frame Length": getattr(layer, 'frame_length', 'N/A'),
                    "Frame Payload": getattr(layer, 'frame_payload', 'N/A'),
                    "Settings Max Table Capacity": getattr(layer, 'settings_qpack_max_table_capacity', 'N/A') if hasattr(layer, 'settings_qpack_max_table_capacity') else ""
                }
                packet_info["HTTP3 Frames"].append(http3_frame_info)

    packets_info.append(packet_info)

output_file = f'{base_dir}/result_files/{case}.json'
with open(output_file, 'w') as f:
    json.dump(packets_info, f, indent=4)



