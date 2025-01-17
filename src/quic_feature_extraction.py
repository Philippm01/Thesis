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
        },
        display_filter='quic'
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
                return True
                
        except AttributeError:
            encrypted_count += 1
            
    print(f"Decrypted packets: {decrypted_count}")
    print(f"Encrypted packets: {encrypted_count}")
    
    return decrypted_count > 0

cap = pyshark.FileCapture(
    pcap_file,
    override_prefs={
        'tls.keylog_file': keylog_file,  
    },
    display_filter='quic'  
)

#TODO: Check if decrytption is working

for packet in cap:
    print(f"Packet Number: {packet.number}")
    print(f"Source IP: {packet.ip.src}")
    print(f"Destination IP: {packet.ip.dst}")
    print(f"Packet Length: {packet.length}")

#TODO: Check how to extract the features from the QUIC packets

    if hasattr(packet, 'quic'):
        print(f"QUIC Stream ID: {getattr(packet.quic, 'stream_id', 'N/A')}")
        print(f"Packet Type: {getattr(packet.quic, 'packet_type', 'N/A')}")
        print(f"Payload: {getattr(packet.quic, 'payload', 'N/A')}")
    print('-' * 50)

pcap_name = extract_pcap_name(pcap_file)
print(f"Extracted PCAP name: {pcap_name}")
print(f"Test string: {case}")


#TODO: Make the same for http3


is_decrypted = verify_decryption(pcap_file, keylog_file)
if not is_decrypted:
    print("Warning: No decrypted packets found!")

print(keylog_file)
print(pcap_file)