import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('json_path', type=str, help='Path to the JSON file')
parser.add_argument('frame_type', type=int, help='Frame type to count')
args = parser.parse_args()

with open(args.json_path, "r") as file:
    data = json.load(file)

frame_type_count = 0
frame_packets = []

for packet in data:
    if "QUIC Frames" in packet:
        for frame in packet["QUIC Frames"]:
            if "Frame Types" in frame and args.frame_type in frame["Frame Types"]:
                frame_packets.append(packet["Packet Number"])
                frame_type_count += 1

if frame_packets:
    print(f"Frames of type {args.frame_type} found in packets: {frame_packets}")
    print(f"Total number of frames of type {args.frame_type}: {frame_type_count}")
else:
    print(f"No frames of type {args.frame_type} found.")