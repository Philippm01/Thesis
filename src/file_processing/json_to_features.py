import json
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.preprocessing import LabelEncoder
from netml.pparser.parser import PCAP
import os
import glob

#-----------------------------Utility Functions--------------------------------

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
        "Frame Type": np.nan
    }

def create_default_http3_frame():
    return {
        "Frame Type": np.nan,
        "Frame Length": np.nan,
        "Settings Max Table Capacity": np.nan
    }

#-----------------------------Feature Extraction--------------------------------

def extract_packet_features(file_path, attack_label):
    MAX_FRAMES = 5
    
    with open(file_path, "r") as f:
        data = json.load(f)

    packets = []
    prev_time = None

    for packet in data:
        quic_frames = packet.get("QUIC Frames", [])
        http3_frames = packet.get("HTTP3 Frames", [])
        if len(quic_frames) > MAX_FRAMES or len(http3_frames) > MAX_FRAMES:
            continue
        
        arrival_time = parse_timestamp(packet["Arrival Time"])
        if arrival_time is None:
            arrival_time = prev_time or datetime.now()
        interarrival_time = (arrival_time - prev_time).total_seconds() if prev_time else 0
        prev_time = arrival_time

        processed_quic_frames = []
        for frame in quic_frames[:MAX_FRAMES]:
            processed_quic_frames.append({
                "Packet Length": safe_int(frame.get("Packet Length")),
                "Packet number": safe_int(frame.get("Packet number")),
                "Length": safe_int(frame.get("Length")),
                "Frame Type": safe_int(frame.get("Frame Type"))
            })
        
        processed_http3_frames = []
        for frame in http3_frames[:MAX_FRAMES]:
            processed_http3_frames.append({
                "Frame Type": safe_int(frame.get("Frame Type")),
                "Frame Length": safe_int(frame.get("Frame Length")),
                "Settings Max Table Capacity": safe_int(frame.get("Settings Max Table Capacity"))
            })

        while len(processed_quic_frames) < MAX_FRAMES:
            processed_quic_frames.append(create_default_quic_frame())
        while len(processed_http3_frames) < MAX_FRAMES:
            processed_http3_frames.append(create_default_http3_frame())

        #Reading all the packet and frame level for each each line
        packet_info = {
            "Packet Number": int(packet["Packet Number"]),
            "Packet Length": int(packet["Packet Length"]),
            "Interarrival Time": interarrival_time,
            "Num QUIC Frames": len(quic_frames),
            "Num HTTP3 Frames": len(http3_frames),
        }

        for i in range(MAX_FRAMES):
            quic_frame = processed_quic_frames[i]
            packet_info.update({
                f"QUIC_Frame_{i+1}_Packet_Length": quic_frame["Packet Length"],
                f"QUIC_Frame_{i+1}_Packet_Number": quic_frame["Packet number"],
                f"QUIC_Frame_{i+1}_Length": quic_frame["Length"],
                f"QUIC_Frame_{i+1}_Type": quic_frame["Frame Type"]
            })
        
        for i in range(MAX_FRAMES):
            http3_frame = processed_http3_frames[i]
            packet_info.update({
                f"HTTP3_Frame_{i+1}_Type": http3_frame["Frame Type"],
                f"HTTP3_Frame_{i+1}_Length": http3_frame["Frame Length"],
                f"HTTP3_Frame_{i+1}_Settings_Capacity": http3_frame["Settings Max Table Capacity"]
            })


        packet_info["Attack Type"] = attack_label
        packets.append(packet_info)

    return pd.DataFrame(packets)

def extract_netml_features(pcap_file, attack_label):
    """Extract NetML features with proper flow handling"""
    pcap = PCAP(pcap_file, flow_ptks_thres=1)
    pcap.pcap2flows()
    
    # Extract specific features using NetML's built-in feature extraction
    pcap.flow2features('STATS', fft=False, header=False)
    features_df = pd.DataFrame(pcap.features)
    
    # Rename and select specific columns
    selected_features = {
        'flow_duration': 'duration',
        'flow_length_packets': 'total_packets',
        'flow_length_packets/flow_duration': 'packets_per_second',
        'flow_length_mean': 'avg_packet_size',
        'flow_length_std': 'std_packet_size',
        'flow_length_min': 'min_packet_size',
        'flow_length_max': 'max_packet_size'
    }
    
    # Create new DataFrame with selected features
    result_df = pd.DataFrame()
    for new_name, old_name in selected_features.items():
        if old_name in features_df.columns:
            result_df[new_name] = features_df[old_name]
        else:
            result_df[new_name] = np.nan
    
    # Add attack label
    result_df['Attack Type'] = attack_label
    
    return result_df

def get_all_files_for_scenario(base_dir, scenario_pattern, start_iteration, end_iteration):

    json_files = []
    pcap_files = []
    
    for i in range(start_iteration, end_iteration + 1):
        json_file = os.path.join(base_dir, "result_files", f"{scenario_pattern}_it:{i}.json")
        pcap_file = os.path.join(base_dir, "packet_capture", f"{scenario_pattern}_it:{i}.pcap")
        
        if os.path.exists(json_file) and os.path.exists(pcap_file):
            json_files.append(json_file)
            pcap_files.append(pcap_file)
        else:
            print(f"file missing in iteration {i}")
    
    return list(zip(json_files, pcap_files))

#-----------------------------Saving to csv files--------------------------------

def create_empty_packet_df():
    """Create empty DataFrame with packet feature columns"""
    columns = [
        "Packet Number", "Packet Length", "Interarrival Time",
        "Num QUIC Frames", "Num HTTP3 Frames"
    ]
    
    # Add QUIC frame columns
    for i in range(1, 6):  # 5 frames
        columns.extend([
            f"QUIC_Frame_{i}_Packet_Length",
            f"QUIC_Frame_{i}_Packet_Number",
            f"QUIC_Frame_{i}_Length",
            f"QUIC_Frame_{i}_Type"
        ])
    
    # Add HTTP3 frame columns
    for i in range(1, 6):  # 5 frames
        columns.extend([
            f"HTTP3_Frame_{i}_Type",
            f"HTTP3_Frame_{i}_Length",
            f"HTTP3_Frame_{i}_Settings_Capacity"
        ])
    
    columns.append("Attack Type")  # Remove Iteration column
    return pd.DataFrame(columns=columns)

def create_empty_session_df():
    columns = [
        "duration", "total_packets", "packets_per_second",
        "avg_packet_size", "std_packet_size", "min_packet_size", "max_packet_size",
        "Attack Type"
    ]
    return pd.DataFrame(columns=columns)

def initialize_csv_files():
    packet_df = create_empty_packet_df()
    session_df = create_empty_session_df()
    
    packet_df.to_csv("all_iterations_quic_packets.csv", index=False)
    session_df.to_csv("all_iterations_quic_sessions.csv", index=False)

def append_to_csv(df, filename):
    df.to_csv(filename, mode='a', header=False, index=False)

#-----------------------------Main function--------------------------------

def process_scenario(attack_type, pattern, base_dir, start_it, end_it):
    files = get_all_files_for_scenario(base_dir, pattern, start_it, end_it)
    packet_count = 0
    session_count = 0
    
    print(f"\nProcessing {attack_type} scenario...")
    
    for json_file, pcap_file in files:
        iteration = json_file.split("_it:")[1].split(".")[0]
        print(f"Processing iteration {iteration}")
        
        try:
            # Process packet features
            packet_features = extract_packet_features(json_file, attack_type)
            append_to_csv(packet_features, "all_iterations_quic_packets.csv")
            packet_count += len(packet_features)
            
            # Process session features with fixed columns
            netml_features = extract_netml_features(pcap_file, attack_type)
            append_to_csv(netml_features, "all_iterations_quic_sessions.csv")
            session_count += len(netml_features)
            
            # Clear memory
            del packet_features
            del netml_features
            
        except Exception as e:
            print(f"Error processing iteration {iteration}: {e}")
            continue
            
    return packet_count, session_count

def main():
    scenarios = {
        "normal": "normal_time:180",
        "flooding": "flood_con:20-50_time:180",
        "slowloris": "slowloris_con:5-10_sleep:20-40_time:180",
        "quicly": "quicly_time:180",
        "lsquic": "lsquic_time:180"
    }
    
    base_dir = '/home/philipp/Documents/Thesis'
    start_iteration = 1  
    end_iteration = 100  
    total_packets = 0
    total_sessions = 0
    
    initialize_csv_files()
    
    for attack_type, pattern in scenarios.items():
        packets, sessions = process_scenario(
            attack_type, 
            pattern, 
            base_dir, 
            start_it=start_iteration, 
            end_it=end_iteration
        )
        total_packets += packets
        total_sessions += sessions
        print(f"Completed {attack_type}: {packets} packets, {sessions} sessions")
    
    print("\nFinal Statistics:")
    print(f"Total packets processed: {total_packets}")
    print(f"Total sessions processed: {total_sessions}")

if __name__ == "__main__":
    main()
