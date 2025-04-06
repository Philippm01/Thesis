import json
import pandas as pd
import numpy as np
from datetime import datetime
import os

def parse_timestamp(time_str):
    time_str = ' '.join(time_str.split())
    if 'CET' in time_str:
        time_str = time_str.replace(' CET', '')
    base_time_str = time_str.split('.')[0]
    microseconds = time_str.split('.')[1][:6] if '.' in time_str else '0'
    base_time = datetime.strptime(base_time_str, "%b %d, %Y %H:%M:%S")
    return base_time.replace(microsecond=int(microseconds))

def safe_int(value):
    try:
        if value == 'N/A' or value is None:
            return np.nan
        return int(value)
    except (ValueError, TypeError):
        return np.nan

def create_default_quic_frame():
    return {
        "Packet Length": np.nan,
        "Packet number": np.nan,
        "Length": np.nan,
        "Frame Types": [np.nan, np.nan, np.nan]
    }

def create_default_http3_frame():
    return {
        "Frame Types": [np.nan, np.nan, np.nan],
        "Frame Length": np.nan,
        "Settings Max Table Capacity": np.nan
    }

def ensure_three_elements(lst):
    return (lst + [np.nan] * 3)[:3]


def extract_packet_features(file_path):
    MAX_QUIC_FRAMES = 2
    MAX_HTTP3_FRAMES = 4
    
    with open(file_path, "r") as f:
        data = json.load(f)

    packets = []
    prev_time = None

    for packet in data:
        try:
            attack_type = int(str(packet.get("Attack Type", "0")))
        except ValueError:
            attack_type = 6
        
        quic_frames = packet.get("QUIC Frames", [])
        http3_frames = packet.get("HTTP3 Frames", [])
        if len(quic_frames) > MAX_QUIC_FRAMES or len(http3_frames) > MAX_HTTP3_FRAMES:
            continue
        
        arrival_time = parse_timestamp(packet["Arrival Time"])
        if arrival_time is None:
            arrival_time = prev_time or datetime.now()
        interarrival_time = (arrival_time - prev_time).total_seconds() if prev_time else 0
        prev_time = arrival_time

        processed_quic_frames = []
        for frame in quic_frames[:MAX_QUIC_FRAMES]:
            processed_quic_frames.append({
                "Packet Length": safe_int(frame.get("Packet Length")),
                "Packet number": safe_int(frame.get("Packet number")),
                "Length": safe_int(frame.get("Length")),
                "Frame Types": ensure_three_elements(frame.get("Frame Types", []))
            })
        
        processed_http3_frames = []
        for frame in http3_frames[:MAX_HTTP3_FRAMES]:
            processed_http3_frames.append({
                "Frame Types": ensure_three_elements(frame.get("Frame Types", [])),
                "Frame Length": safe_int(frame.get("Frame Length")),
                "Settings Max Table Capacity": safe_int(frame.get("Settings Max Table Capacity"))
            })

        while len(processed_quic_frames) < MAX_QUIC_FRAMES:
            processed_quic_frames.append(create_default_quic_frame())
        while len(processed_http3_frames) < MAX_HTTP3_FRAMES:
            processed_http3_frames.append(create_default_http3_frame())

        packet_info = {
            "Packet Length": int(packet["Packet Length"]),
            "Interarrival Time": interarrival_time,
            "Num QUIC Frames": len(quic_frames),
            "Num HTTP3 Frames": len(http3_frames),
        }

        for i in range(MAX_QUIC_FRAMES):
            quic_frame = processed_quic_frames[i]
            packet_info.update({
                f"QUIC_Frame_{i+1}_Packet_Length": quic_frame["Packet Length"],
                f"QUIC_Frame_{i+1}_Packet_Number": quic_frame["Packet number"],
                f"QUIC_Frame_{i+1}_Length": quic_frame["Length"],
                f"QUIC_Frame_{i+1}_Type_1": quic_frame["Frame Types"][0],
                f"QUIC_Frame_{i+1}_Type_2": quic_frame["Frame Types"][1],
                f"QUIC_Frame_{i+1}_Type_3": quic_frame["Frame Types"][2]
            })
        
        for i in range(MAX_HTTP3_FRAMES):
            http3_frame = processed_http3_frames[i]
            packet_info.update({
                f"HTTP3_Frame_{i+1}_Type_1": http3_frame["Frame Types"][0],
                f"HTTP3_Frame_{i+1}_Type_2": http3_frame["Frame Types"][1],
                f"HTTP3_Frame_{i+1}_Type_3": http3_frame["Frame Types"][2],
                f"HTTP3_Frame_{i+1}_Length": http3_frame["Frame Length"],
                f"HTTP3_Frame_{i+1}_Settings_Capacity": http3_frame["Settings Max Table Capacity"]
            })

        packet_info["Attack Type"] = attack_type

        packets.append(packet_info)

    df = pd.DataFrame(packets)
    df = df.fillna(0)
    expected_columns = create_empty_packet_df().columns.tolist()
    df = df.reindex(columns=expected_columns)
    
    return df

def create_empty_packet_df():
    columns = [
        "Packet Length", "Interarrival Time",
        "Num QUIC Frames", "Num HTTP3 Frames"
    ]
    
    for i in range(1, 3):  
        columns.extend([
            f"QUIC_Frame_{i}_Packet_Length",
            f"QUIC_Frame_{i}_Packet_Number",
            f"QUIC_Frame_{i}_Length",
            f"QUIC_Frame_{i}_Type_1",
            f"QUIC_Frame_{i}_Type_2",
            f"QUIC_Frame_{i}_Type_3"
        ])
    
    for i in range(1, 5): 
        columns.extend([
            f"HTTP3_Frame_{i}_Type_1",
            f"HTTP3_Frame_{i}_Type_2",
            f"HTTP3_Frame_{i}_Type_3",
            f"HTTP3_Frame_{i}_Length",
            f"HTTP3_Frame_{i}_Settings_Capacity"
        ])
    
    columns.append("Attack Type")
    return pd.DataFrame(columns=columns)

def initialize_csv_files():
    packet_df = create_empty_packet_df()
    packet_df.to_csv("all_iterations_quic_packets.csv", index=False)

def append_to_csv(df, filename):
    df.to_csv(filename, mode='a', header=False, index=False)

def process_all_json_files(base_dir):
    json_dir = os.path.join(base_dir, "result_files")
    json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]
    packet_count = 0

    print(f"\nProcessing all JSON files in {json_dir}...")

    for json_file in json_files:
        file_path = os.path.join(json_dir, json_file)
        print(f"Processing file: {json_file}")

        try:
            packet_features = extract_packet_features(file_path)
            
            if "Attack Type" in packet_features.columns:
                print(f"Attack Type column exists with values: {packet_features['Attack Type'].value_counts().to_dict()}")
            else:
                print("Attack Type column is missing!")
            
            append_to_csv(packet_features, "all_iterations_quic_packets.csv")
            packet_count += len(packet_features)

            del packet_features

        except Exception as e:
            print(f"Error processing file {json_file}: {e}")
            continue

    return packet_count

def main():
    base_dir = '/home/philipp/Documents/Thesis'
    total_packets = 0

    initialize_csv_files()

    total_packets = process_all_json_files(base_dir)

    print("\nFinal Statistics:")
    print(f"Total packets processed: {total_packets}")

if __name__ == "__main__":
    main()
