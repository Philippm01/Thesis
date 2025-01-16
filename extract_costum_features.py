import pyshark

# Path to the PCAP file
pcap_file = '/home/philipp/Documents/Thesis/packet_capture/flood_con:10-15_time:20.pcap'

# Path to the TLS key log file
keylog_file = '/home/philipp/Documents/Thesis/secrets_files/flood_con:10-15_time:20.txt'

# Load the PCAP file with TLS decryption enabled
cap = pyshark.FileCapture(
    pcap_file,
    override_prefs={
        'tls.keylog_file': keylog_file,  # Enable decryption with the key log file
        # Remove 'quic.desegment_payload' preference
    },
    display_filter='quic'  # Optional: Focus on QUIC packets
)

# Process QUIC packets
for packet in cap:
    print(f"Packet Number: {packet.number}")
    print(f"Source IP: {packet.ip.src}")
    print(f"Destination IP: {packet.ip.dst}")
    print(f"Packet Length: {packet.length}")

    # Extract QUIC-specific fields
    if hasattr(packet, 'quic'):
        print(f"QUIC Stream ID: {getattr(packet.quic, 'stream_id', 'N/A')}")
        print(f"Packet Type: {getattr(packet.quic, 'packet_type', 'N/A')}")
        print(f"Payload: {getattr(packet.quic, 'payload', 'N/A')}")
    print('-' * 50)
