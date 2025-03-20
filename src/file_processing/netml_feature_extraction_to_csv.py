import os
import pandas as pd
from netml.pparser.parser import PCAP
from functools import reduce
import re
import numpy as np
from sklearn.impute import SimpleImputer

COMMON_FEATURES = None

def extract_netml_features(pcap_file, common_features):
    print(f"Reading PCAP file: {pcap_file}")
    base_dir = '/home/philipp/Documents/Thesis'
    pcap_dir = os.path.join(base_dir, "packet_capture")
    pcap_path = os.path.join(pcap_dir, pcap_file)
    pcap = PCAP(pcap_path, flow_ptks_thres=2)
    pcap.pcap2flows()

    feature_types = ['IAT', 'STATS', 'SIZE', 'SAMP_NUM', 'SAMP_SIZE']
    feature_frames = []

    for feature_type in feature_types:
        pcap.flow2features(feature_type, fft=False, header=False)
        df = pd.DataFrame(pcap.features)
        df.columns = [f"{feature_type}_{col}" for col in df.columns]
        feature_frames.append(df)
    
    all_features = pd.concat(feature_frames, axis=1)
    all_features = all_features[sorted(common_features)]
    
    return all_features

def determine_common_features(pcap_dir):
    global COMMON_FEATURES
    
    normal_stats_features = []
    
    for filename in os.listdir(pcap_dir):
        if filename.startswith("normal_") and filename.endswith(".pcap"):
            pcap_file = os.path.join(pcap_dir, filename)
            try:
                pcap = PCAP(pcap_file, flow_ptks_thres=2)
                pcap.pcap2flows()

                feature_types = ['IAT', 'STATS', 'SIZE', 'SAMP_NUM', 'SAMP_SIZE']
                feature_frames = []

                for feature_type in feature_types:
                    pcap.flow2features(feature_type, fft=False, header=False)
                    df = pd.DataFrame(pcap.features)
                    df.columns = [f"{feature_type}_{col}" for col in df.columns]
                    feature_frames.append(df)
    
                all_features = pd.concat(feature_frames, axis=1)
                stats_features = {col for col in all_features.columns if col.startswith("STATS")}
                normal_stats_features.append(stats_features)
            except Exception as e:
                print(f"Error processing file {filename}: {e}")
    
    if normal_stats_features:
        COMMON_FEATURES = set.intersection(*normal_stats_features)
    else:
        COMMON_FEATURES = set()
    
    print(f"Common STATS features across all normal PCAP files: {len(COMMON_FEATURES)}")
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
            features_df = extract_netml_features(pcap_file, COMMON_FEATURES)
            features_df = features_df.reindex(sorted(features_df.columns, key=lambda x: int("".join(filter(str.isdigit, x)))), axis=1)
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

    COMMON_FEATURES = determine_common_features(pcap_dir)

    for filename in os.listdir(pcap_dir):
        if filename.endswith(".pcap"):
            scenario = filename.split('_')[0]
            output_dir = os.path.join(output_base_dir, scenario)
            
            attack_label = attack_labels.get(scenario, -1)
            
            process_pcap_file(pcap_dir, filename, output_dir, attack_label)

if __name__ == "__main__":
    main()