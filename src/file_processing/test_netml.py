import os
from netml.pparser.parser import PCAP
import pandas as pd
import argparse

def extract_netml_features(pcap_file):
    print(f"Reading PCAP file: {pcap_file}")
    base_dir = '/home/philipp/Documents/Thesis'
    pcap_dir = os.path.join(base_dir, "packet_capture")
    pcap_path = os.path.join(pcap_dir, pcap_file)
    try:
        pcap = PCAP(pcap_path, flow_ptks_thres=1)
        pcap.pcap2flows()

        feature_types = ['IAT', 'STATS', 'SIZE', 'SAMP_NUM', 'SAMP_SIZE']
        feature_names = []

        for feature_type in feature_types:
            pcap.flow2features(feature_type, fft=False, header=True)
            if hasattr(pcap, 'fieldnames'):
                feature_names.extend([f"{feature_type}_{col}" for col in pcap.fieldnames])
            else:
                feature_names.extend([f"{feature_type}_{i+1}" for i in range(len(pcap.features[0]))])

        return feature_names
    except (RuntimeError, IndexError) as e:
        print(f"Error processing PCAP file {pcap_file}: {e}")
        return []

def main():
    base_dir = '/home/philipp/Documents/Thesis'
    pcap_dir = os.path.join(base_dir, "packet_capture")
    
    feature_types = ['IAT', 'STATS', 'SIZE', 'SAMP_NUM', 'SAMP_SIZE']
    
    results = []
    
    for filename in sorted(os.listdir(pcap_dir)):
        if filename.endswith(".pcap"):
            full_pcap_path = os.path.join(pcap_dir, filename)
            if os.path.exists(full_pcap_path):
                feature_names = extract_netml_features(filename)
                
                feature_counts = {
                    feature_type: sum(1 for feature in feature_names if feature.startswith(feature_type))
                    for feature_type in feature_types
                }
                
                results.append({
                    "filename": filename,
                    **feature_counts
                })
            else:
                print(f"PCAP file not found: {filename}")
    
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values(by="filename")
        
        output_csv_path = os.path.join(base_dir, "feature_counts.csv")
        df.to_csv(output_csv_path, index=False)
        print(f"Feature counts saved to {output_csv_path}")
    else:
        print("No PCAP files were successfully processed.")

if __name__ == "__main__":
    main()
