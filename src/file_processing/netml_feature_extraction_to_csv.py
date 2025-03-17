import os
import pandas as pd
from netml.pparser.parser import PCAP
from functools import reduce
import re
import numpy as np
from sklearn.impute import SimpleImputer

COMMON_FEATURES = None

def extract_netml_features(pcap_file, common_features=None):
    print(f"Reading PCAP file: {pcap_file}")
    pcap = PCAP(pcap_file, flow_ptks_thres=1)
    pcap.pcap2flows()

    feature_types = ['IAT', 'STATS', 'SIZE', 'SAMP_NUM', 'SAMP_SIZE']
    feature_frames = []

    for feature_type in feature_types:
        pcap.flow2features(feature_type, fft=False, header=False)
        df = pd.DataFrame(pcap.features)
        df.columns = [f"{feature_type}_{col}" for col in df.columns]
        feature_frames.append(df)
    
    all_features = pd.concat(feature_frames, axis=1)
    
    if common_features is not None:
        all_features = all_features[sorted(common_features)]
    
    imputer = SimpleImputer(strategy='mean')
    all_features = pd.DataFrame(imputer.fit_transform(all_features), columns=all_features.columns)
    
    return all_features

def determine_common_features(pcap_dir):
    global COMMON_FEATURES
    all_features = {}
    feature_counts = {}

    for filename in os.listdir(pcap_dir):
        if filename.endswith(".pcap"):
            pcap_file = os.path.join(pcap_dir, filename)
            try:
                features_df = extract_netml_features(pcap_file)
                
                for col in features_df.columns:
                    if col not in feature_counts:
                        feature_counts[col] = 0
                    feature_counts[col] += features_df[col].count()
                
                all_features[filename] = set(features_df.columns)
            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    sorted_features = sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)
    top_50_features = [feature for feature, count in sorted_features[:50]]
    
    COMMON_FEATURES = set(top_50_features) if top_50_features else set()
    print(f"Top 50 common features across all PCAP files: {len(COMMON_FEATURES)}")
    return COMMON_FEATURES

def process_pcap_file(pcap_dir, pcap_file, output_dir, attack_label):
    global COMMON_FEATURES

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pcap_path = os.path.join(pcap_dir, pcap_file)
    csv_file = os.path.join(output_dir, pcap_file.replace(".pcap", ".csv"))

    if os.path.exists(pcap_path):
        print(f"Processing file: {pcap_path}")
        try:
            features_df = extract_netml_features(pcap_path, COMMON_FEATURES)
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
            scenario = filename.split('_')[0]
            output_dir = os.path.join(output_base_dir, scenario)
            
            attack_label = attack_labels.get(scenario, -1)
            
            process_pcap_file(pcap_dir, filename, output_dir, attack_label)

if __name__ == "__main__":
    main()