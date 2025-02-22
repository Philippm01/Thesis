import pandas as pd
import numpy as np
from netml.pparser.parser import PCAP
import os

def extract_netml_features(pcap_file, attack_label):
    pcap = PCAP(pcap_file, flow_ptks_thres=1)
    pcap.pcap2flows()
    pcap.flow2features('STATS', fft=False, header=False)
    features_df = pd.DataFrame(pcap.features)
    
    selected_features = {
        'flow_duration': 'duration',
        'flow_length_packets': 'total_packets',
        'flow_length_packets/flow_duration': 'packets_per_second',
        'flow_length_mean': 'avg_packet_size',
        'flow_length_std': 'std_packet_size',
        'flow_length_min': 'min_packet_size',
        'flow_length_max': 'max_packet_size'
    }
    
    result_df = pd.DataFrame()
    for new_name, old_name in selected_features.items():
        if old_name in features_df.columns:
            result_df[new_name] = features_df[old_name]
        else:
            result_df[new_name] = np.nan
    
    result_df['Attack Type'] = attack_label
    
    return result_df

def create_empty_session_df():
    columns = [
        "duration", "total_packets", "packets_per_second",
        "avg_packet_size", "std_packet_size", "min_packet_size", "max_packet_size",
        "Attack Type"
    ]
    return pd.DataFrame(columns=columns)

def initialize_csv_files():
    session_df = create_empty_session_df()
    session_df.to_csv("all_iterations_quic_sessions.csv", index=False)

def append_to_csv(df, filename):
    df.to_csv(filename, mode='a', header=False, index=False)

def process_scenario(attack_type, pattern, base_dir, start_it, end_it):
    files = get_all_files_for_scenario(base_dir, pattern, start_it, end_it)
    session_count = 0
    
    print(f"\nProcessing {attack_type} scenario...")
    
    for _, pcap_file in files:
        iteration = pcap_file.split("_it:")[1].split(".")[0]
        print(f"Processing iteration {iteration}")
        
        try:
            netml_features = extract_netml_features(pcap_file, attack_type)
            append_to_csv(netml_features, "all_iterations_quic_sessions.csv")
            session_count += len(netml_features)
            
            del netml_features
            
        except Exception as e:
            print(f"Error processing iteration {iteration}: {e}")
            continue
            
    return session_count

def get_all_files_for_scenario(base_dir, scenario_pattern, start_iteration, end_iteration):
    pcap_files = []
    
    for i in range(start_iteration, end_iteration + 1):
        pcap_file = os.path.join(base_dir, "packet_capture", f"{scenario_pattern}_it:{i}.pcap")
        
        if os.path.exists(pcap_file):
            pcap_files.append(pcap_file)
        else:
            print(f"file missing in iteration {i}")
    
    return [(None, pcap_file) for pcap_file in pcap_files]

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
    total_sessions = 0
    
    initialize_csv_files()
    
    for attack_type, pattern in scenarios.items():
        sessions = process_scenario(
            attack_type, 
            pattern, 
            base_dir, 
            start_it=start_iteration, 
            end_it=end_iteration
        )
        total_sessions += sessions
        print(f"Completed {attack_type}: {sessions} sessions")
    
    print("\nFinal Statistics:")
    print(f"Total sessions processed: {total_sessions}")

if __name__ == "__main__":
    main()
