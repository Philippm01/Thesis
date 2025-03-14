import os
import pandas as pd
from netml.pparser.parser import PCAP
from functools import reduce
import re

COMMON_FEATURES = None

def extract_netml_features(pcap_file):
    """Extract NetML features and ensure a consistent feature set."""
    print(f"Reading PCAP file: {pcap_file}")
    pcap = PCAP(pcap_file, flow_ptks_thres=2)
    pcap.pcap2flows()

    # Extract features from all categories
    feature_types = ['IAT', 'STATS', 'SIZE', 'SAMP_NUM', 'SAMP_SIZE']
    feature_frames = []

    for feature_type in feature_types:
        pcap.flow2features(feature_type, fft=False, header=False)
        df = pd.DataFrame(pcap.features)
        df.columns = [f"{feature_type}_{col}" for col in df.columns]
        feature_frames.append(df)
    
    # Combine all feature DataFrames
    all_features = pd.concat(feature_frames, axis=1)
    return all_features

def determine_common_features(pcap_dir):
    """Determine the set of features that are common across all PCAP files."""
    global COMMON_FEATURES
    all_features = {}

    # Collect all features from each PCAP file
    for filename in os.listdir(pcap_dir):
        if filename.endswith(".pcap"):
            pcap_file = os.path.join(pcap_dir, filename)
            try:
                features_df = extract_netml_features(pcap_file)
                all_features[filename] = set(features_df.columns)
            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    COMMON_FEATURES = reduce(lambda x, y: x & y, all_features.values()) if all_features else set()
    print(f"Common features across all PCAP files: {len(COMMON_FEATURES)}")
    return COMMON_FEATURES

def process_pcap_file(pcap_dir, pcap_file, output_dir, attack_label):
    """Process a single PCAP file and save extracted features as a CSV file."""
    global COMMON_FEATURES

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pcap_path = os.path.join(pcap_dir, pcap_file)
    csv_file = os.path.join(output_dir, pcap_file.replace(".pcap", ".csv"))

    if os.path.exists(pcap_path):
        print(f"Processing file: {pcap_path}")
        try:
            features_df = extract_netml_features(pcap_path)
            
            features_df = features_df[sorted(COMMON_FEATURES)]
            
            # Add the attack label
            features_df['attack'] = attack_label
            
            # Save to CSV
            features_df.to_csv(csv_file, index=False, header=True)
            print(f"Features saved to {csv_file}")

        except Exception as e:
            print(f"Error processing file {pcap_path}: {e}")
    else:
        print(f"File missing: {pcap_path}")

def main():
    base_dir = '/home/philipp/Documents/Thesis'
    pcap_dir = os.path.join(base_dir, "packet_capture")
    output_base_dir = os.path.join(base_dir, "session_Datasets")
    
    # Define attack labels based on directory names
    attack_labels = {
        "normal": 0,
        "flooding": 1,
        "slowloris": 2,
        "quicly": 3,
        "lsquic": 4
    }

    determine_common_features(pcap_dir)

    for filename in os.listdir(pcap_dir):
        if filename.endswith(".pcap"):
            # Infer scenario from filename (example: "normal_time:180_it:1.pcap" -> "normal")
            scenario = filename.split('_')[0]
            output_dir = os.path.join(output_base_dir, scenario)
            
            # Get the attack label
            attack_label = attack_labels.get(scenario, -1)  # Default to -1 if not found
            
            process_pcap_file(pcap_dir, filename, output_dir, attack_label)

if __name__ == "__main__":
    main()