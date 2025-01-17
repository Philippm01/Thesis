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
    
    for packet in cap:
        try:
            # Check for decrypted QUIC layer
            if hasattr(packet, 'quic'):
                if hasattr(packet.quic, 'payload'):
                    decrypted_count += 1
                else:
                    encrypted_count += 1
                    
            # Check for HTTP3 layer
            if hasattr(packet, 'http3'):
                print(f"Found HTTP3 layer in packet {packet.number}")
                
        except AttributeError:
            encrypted_count += 1

    return decrypted_count, encrypted_count

cap = pyshark.FileCapture(
    pcap_file,
    override_prefs={
        'tls.keylog_file': keylog_file,
        'tls.desegment_ssl_records': 'TRUE',
        'tls.desegment_ssl_application_data': 'TRUE',
    },
)

# Extract features from QUIC packets
for packet in cap:
    print(f"Packet Number: {packet.number}")
    print(f"Source IP: {packet.ip.src}")
    print(f"Destination IP: {packet.ip.dst}")
    print(f"Packet Length: {packet.length}")

    if hasattr(packet, 'quic'):
        print(f"QUIC Stream ID: {getattr(packet.quic, 'stream_id', 'N/A')}")
        print(f"Frame Type: {getattr(packet.quic, 'frame_type', 'N/A')}")
        if hasattr(packet.quic, 'payload'):
            print(f"Payload (Decrypted): {packet.quic.payload}")
        
    if hasattr(packet, 'http3'):
        print("HTTP3 Layer Found:")
        print(f"Stream Type: {getattr(packet.http3, 'stream_type', 'N/A')}")
        print(f"Frame Type: {getattr(packet.http3, 'frame_type', 'N/A')}")
        print(f"Frame Payload: {getattr(packet.http3, 'frame_payload', 'N/A')}")
    print('-' * 50)

pcap_name = extract_pcap_name(pcap_file)
print(f"Extracted PCAP name: {pcap_name}")
print(f"Test string: {case}")

# Check if decryption is working
decrypted_count, encrypted_count = verify_decryption(pcap_file, keylog_file)
print(f"Decrypted packets: {decrypted_count}")
print(f"Encrypted packets: {encrypted_count}")
