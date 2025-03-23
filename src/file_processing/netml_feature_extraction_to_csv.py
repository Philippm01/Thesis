import os
import pandas as pd
from netml.pparser.parser import PCAP
from functools import reduce
import re
import numpy as np
from sklearn.impute import SimpleImputer
import argparse

COMMON_FEATURES = None

def extract_netml_features(pcap_file):
    print(f"Reading PCAP file: {pcap_file}")
    base_dir = '/home/philipp/Documents/Thesis'
    pcap_dir = os.path.join(base_dir, "packet_capture")
    pcap_path = os.path.join(pcap_dir, pcap_file)
    try:
        pcap = PCAP(pcap_path, flow_ptks_thres=2)
        pcap.pcap2flows()

        feature_types = ['STATS']
        feature_frames = []

        for feature_type in feature_types:
            pcap.flow2features(feature_type, fft=False, header=False)
            if pcap.features is not None:
                df = pd.DataFrame(pcap.features)
                df.columns = [f"{feature_type}_{col}" for col in df.columns]
                feature_frames.append(df)
            else:
                print(f"No features extracted for {pcap_file} using {feature_type}")
                return None
    
        if feature_frames:
            all_features = pd.concat(feature_frames, axis=1)
            return all_features
        else:
            print(f"No feature frames to concatenate for {pcap_file}")
            return None

    except (RuntimeError, IndexError) as e:
        print(f"Error processing PCAP file {pcap_file}: {e}")
        return None

def process_pcap_file(pcap_dir, pcap_file, output_dir, prefix=None):
    global COMMON_FEATURES

    if prefix and not pcap_file.startswith(prefix):
        print(f"Skipping {pcap_file} as it does not start with prefix '{prefix}'.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pcap_path = os.path.join(pcap_dir, pcap_file)
    csv_file = os.path.join(output_dir, pcap_file.replace(".pcap", ".csv"))

    if os.path.exists(pcap_path):
        print(f"Processing file: {pcap_path}")
        try:
            features_df = extract_netml_features(pcap_file)
            if features_df is not None:
                features_df = features_df.reindex(sorted(features_df.columns, key=lambda x: int("".join(filter(str.isdigit, x)))), axis=1)
                features_df.to_csv(csv_file, index=False, header=True)
                print(f"Features saved to {csv_file}")
            else:
                print(f"No features extracted from {pcap_file}, skipping CSV creation.")

        except Exception as e:
            print(f"Error processing file {pcap_path}: {e}")
    else:
        print(f"File missing: {pcap_path}")

def main():
    base_dir = '/home/philipp/Documents/Thesis'
    pcap_dir = os.path.join(base_dir, "packet_capture")
    output_base_dir = os.path.join(base_dir, "session_Datasets")
    
    parser = argparse.ArgumentParser(description="Extract NetML features from PCAP files.")
    parser.add_argument("--prefix", type=str, help="Process only files starting with this prefix.")
    args = parser.parse_args()

    for filename in os.listdir(pcap_dir):
        if filename.endswith(".pcap"):
            scenario = filename.split('_')[0]
            output_dir = os.path.join(output_base_dir, scenario)
            
            process_pcap_file(pcap_dir, filename, output_dir, args.prefix)

if __name__ == "__main__":
    main()