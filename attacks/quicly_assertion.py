import hmac
import hashlib
import binascii
import struct
from scapy.all import *
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import socket
import os
import argparse
import random

def send_and_receive_quic(hex_string, destination_ip, destination_port, source_port, is_first_packet, timeout=5):
    packet_bytes = bytes.fromhex(hex_string)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", source_port))
    sock.settimeout(timeout)

    try:
        sock.sendto(packet_bytes, (destination_ip, destination_port))
        print(f"Sent QUIC packet from port {source_port}")

        if not is_first_packet: 
            return

        data, addr = sock.recvfrom(65535)
        print(f"Received response from {addr}: {data.hex()}")
        return data.hex()

    except socket.timeout:
        print("No response received within timeout.")
    finally:
        sock.close()

def extract_new_dcid(response_hex: str) -> str:
    skip_hex_chars = 14 
    length_to_extract = 16  
    return response_hex[skip_hex_chars : skip_hex_chars + length_to_extract]

def hkdf_extract(salt_hex: str, ikm_hex: str) -> str:
    if not salt_hex:
        salt_hex = "0" * 64
    
    salt = binascii.unhexlify(salt_hex)
    ikm = binascii.unhexlify(ikm_hex)
    
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    return binascii.hexlify(prk).decode('ascii')

def hkdf_expand(prk_hex: str, info_hex: str, length: int) -> str:

    prk = binascii.unhexlify(prk_hex)
    info = binascii.unhexlify(info_hex) if info_hex else b""
    
    n = (length + 31) // 32  
    t = b""
    output = b""
    
    for i in range(1, n + 1):
        data = t + info + bytes([i])
        t = hmac.new(prk, data, hashlib.sha256).digest()
        output += t
    
    return binascii.hexlify(output[:length]).decode('ascii')

def hkdf_expand_label(prk_hex: str, label: str, context_hex: str, length: int) -> str:
    label_bytes = f"tls13 {label}".encode()
    context = binascii.unhexlify(context_hex) if context_hex else b""
    
    hkdf_label = (
        struct.pack("!H", length) +                   
        struct.pack("!B", len(label_bytes)) +          
        label_bytes +                                 
        struct.pack("!B", len(context)) +              
        context                                       
    )
    info_hex = binascii.hexlify(hkdf_label).decode('ascii')
    return hkdf_expand(prk_hex, info_hex, length)

def get_packet_length_hex(payload_hex: str) -> str:
    payload_bytes = bytes.fromhex(payload_hex)
    packet_length = len(payload_bytes)
    packet_length_hex = format(packet_length, 'x').zfill(4)  
    return packet_length_hex

def validate_hex(hex_string):
    clean_hex = ''.join(hex_string.split())
    try:
        bytes.fromhex(clean_hex)
        return clean_hex
    except ValueError as e:
        print(f"Error: {str(e).split()[-1]}")
        return None

def packet_number_to_hex(packet_number: int, packet_number_length: int) -> str:
    return packet_number.to_bytes(packet_number_length, byteorder='big').hex()

def get_random_cid() -> str:
    random_bytes = os.urandom(8)
    return random_bytes.hex()

def get_enrypted_payload_length(DCID, packet_number, header, plaintext_payload):

    INITIAL_SALT_V1 = "38762cf7f55934b34d179ae6a4c80cadccbb7f0a"
    initial_secret = hkdf_extract(INITIAL_SALT_V1, DCID)
    print(f"Initial Secret: {initial_secret}")
    client_secret = hkdf_expand_label(initial_secret,"client in", "", 32)
    print(f"Client Secret: {client_secret}")
    client_initial_key = hkdf_expand_label(client_secret,"quic key","",16)
    print(f"Client key: {client_initial_key}")
    client_iv = hkdf_expand_label(client_secret,"quic iv","",12)
    print(f"Client IV: {client_iv}")
    client_header_protection_keys = hkdf_expand_label(client_secret, "quic hp", "", 16)
    print(f"Client Header Protection Keys: {client_header_protection_keys}")

    client_iv_bytes = bytes.fromhex(client_iv)  
    nonce = int.from_bytes(client_iv_bytes, "big") ^ packet_number
    nonce_bytes = nonce.to_bytes(12, byteorder="big")

    plaintext_payload_bytes = bytes.fromhex(plaintext_payload)
    header_bytes = bytes.fromhex(header)

    aesgcm = AESGCM(bytes.fromhex(client_initial_key))
    encrypted_payload = aesgcm.encrypt(nonce_bytes, plaintext_payload_bytes, header_bytes)

    encrypted_payload_length = len(encrypted_payload) + 4
    hex_value = hex(encrypted_payload_length)[2:]
    return f"4{hex_value}"
  
def get_initial_secrets(DCID):
    
    INITIAL_SALT_V1 = "38762cf7f55934b34d179ae6a4c80cadccbb7f0a"

    initial_secret = hkdf_extract(INITIAL_SALT_V1, DCID)
    print(f"Initial Secret: {initial_secret}")
    client_secret = hkdf_expand_label(initial_secret,"client in", "", 32)
    print(f"Client Secret: {client_secret}")
    client_initial_key = hkdf_expand_label(client_secret,"quic key","",16)
    print(f"Client key: {client_initial_key}")
    client_iv = hkdf_expand_label(client_secret,"quic iv","",12)
    print(f"Client IV: {client_iv}")
    client_header_protection_keys = hkdf_expand_label(client_secret, "quic hp", "", 16)
    print(f"Client Header Protection Keys: {client_header_protection_keys}")
    return initial_secret, client_secret, client_initial_key, client_iv, client_header_protection_keys

def get_valid_packet(packet_number, packet_number_length, header, plaintext_payload, client_initial_key, client_iv, client_header_protection_keys):

    ######################## Payload Protection #############################

    client_iv_bytes = bytes.fromhex(client_iv)  
    nonce = int.from_bytes(client_iv_bytes, "big") ^ packet_number
    nonce_bytes = nonce.to_bytes(12, byteorder="big")

    plaintext_payload_bytes = bytes.fromhex(plaintext_payload)
    header_bytes = bytes.fromhex(header)


    print(f"Header given to aead: \n{header_bytes.hex()}")

    aesgcm = AESGCM(bytes.fromhex(client_initial_key))
    encrypted_payload = aesgcm.encrypt(nonce_bytes, plaintext_payload_bytes, header_bytes)

    encrypted_payload_hex = encrypted_payload.hex()
    print(f"Encrypted Payload (hex): \n{encrypted_payload_hex}")

    ################################# Header Protection ################################

    quic_packet = header_bytes + encrypted_payload
    sample_offset = (len(header_bytes) - packet_number_length) + 4
    sample_length = 16
    sample = quic_packet[sample_offset : sample_offset + sample_length]
    print(f"Sample : {sample.hex()}")

    ############################ Generate Header Protection Mask ############################
    
    hp_key_bytes = bytes.fromhex(client_header_protection_keys)
    cipher = Cipher(algorithms.AES(hp_key_bytes), modes.ECB())
    encryptor = cipher.encryptor()
    mask = encryptor.update(sample)[:5]
    print(f"Mask : {mask.hex()}")

    header_list = bytearray(header_bytes)  
    header_list[0] ^= (mask[0] & 0x0F)
    pn_offset = len(header_list) - packet_number_length

    for i in range(packet_number_length):
        header_list[pn_offset + i] ^= mask[i + 1]

    ##############################Generate Final Packet####################################

    final_packet = bytes(header_list) + encrypted_payload
    print(f"Masked header : {header_list.hex()}")
    return final_packet

def generate_padding(total_length: int, basic_frame: str) -> str:
    current_bytes = len(basic_frame) // 2
    padding_bytes_needed = total_length - current_bytes
    padding = "00" * padding_bytes_needed
    
    return padding

def get_random_port(min_port: int, max_port: int) -> int:
    return random.randint(min_port, max_port)

def parse_arguments():
    parser = argparse.ArgumentParser(description='QUIC Client with customizable connection parameters')
    parser.add_argument('--ip', 
                      default='127.0.0.1',
                      help='Destination IP address')
    parser.add_argument('--dport',
                      type=int,
                      default=4433,
                      help='Destination port')
    parser.add_argument('--sport-min',
                      type=int,
                      default=10000,
                      help='Minimum source port')
    parser.add_argument('--sport-max',
                      type=int,
                      default=60000,
                      help='Maximum source port')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    destination_ip = args.ip
    destination_port = args.dport
    source_port = get_random_port(args.sport_min, args.sport_max)

    # TLS Client Hello with Connection Close frame 
    Crpyto_frame= "0600411f0100011b0303b1804826247d5e392fd69edfa8b9f87629f12937934e61b44ec5a87693f16256000006130213011303010000ec0033004700450017004104938a26bea057343c8840494372005eb56530d8cc2a2533cccfebabfc431bd57b2b8844d804e67a7784b0f9ab5b4174021a348c041e6531f271983067b9ef4776002b0003020304000d000a00080804040304010201000a0004000200170039003b030245c00504801000000604801000000704801000000404810000000104800075300f00080240640a010ac0000000ff03de1a04800061a80e0104ffa5003b030245c00504801000000604801000000704801000000404810000000104800075300f00080240640a010ac0000000ff03de1a04800061a80e0104002d00020101"
    Connection_close_frame = "1c000000"
    Paddding = generate_padding(1200, Crpyto_frame + Connection_close_frame)
    plaintext_payload = Crpyto_frame + Connection_close_frame + Paddding
    print(f"{plaintext_payload}\n")
    Initial_byte = "c3"
    Version = "00000001"
    dcid_length = "08"
    DCID = get_random_cid()
    scid_length = "00"
    SCID = ""
    Token = "00"
    packet_number = 0
    packet_number_length = 4
    packet_number_hex = packet_number_to_hex(packet_number, packet_number_length)
    dummy_header = Initial_byte + Version + dcid_length + DCID + scid_length + SCID + Token + "0000" + packet_number_hex
    Packet_length = get_enrypted_payload_length(DCID, packet_number, dummy_header , plaintext_payload)
    header = Initial_byte + Version + dcid_length + DCID + scid_length + SCID + Token + Packet_length + packet_number_hex
    initial_secret, client_secret, client_initial_key, client_iv, client_header_protection_keys = get_initial_secrets(DCID)
    hex_string = get_valid_packet(packet_number, packet_number_length, header, plaintext_payload, client_initial_key, client_iv, client_header_protection_keys).hex()
    response = send_and_receive_quic(hex_string, destination_ip, destination_port, source_port, 1)

    # Ack frame to trigger the assertion
    ack = "020040b800"
    plaintext_payload = ack + generate_padding(1200, ack)
    DCID = extract_new_dcid(response)
    print(f"New DCID: {DCID}")
    packet_number = 1
    packet_number_length = 4
    packet_number_hex = packet_number_to_hex(packet_number, packet_number_length)
    dummy_header = Initial_byte + Version + dcid_length + DCID + scid_length + SCID + Token + "0000" + packet_number_hex
    Packet_length = get_enrypted_payload_length(DCID, packet_number, dummy_header , plaintext_payload)
    header = Initial_byte + Version + dcid_length + DCID + scid_length + SCID + Token + Packet_length + packet_number_hex
    hex_string2 = get_valid_packet(packet_number, packet_number_length, header, plaintext_payload, client_initial_key, client_iv, client_header_protection_keys).hex()
    send_and_receive_quic(hex_string2, destination_ip, destination_port, source_port, 0)


