import os
import pandas as pd
from netml.pparser.parser import PCAP
from functools import reduce

# Change from ALL_FEATURES to COMMON_FEATURES
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
        df.columns = [f"{feature_type}_{col}" for col in df.columns]  # Prefix columns with feature type
        feature_frames.append(df)
    
    # Combine all feature DataFrames
    all_features = pd.concat(feature_frames, axis=1)
    return all_features

def determine_common_features(base_dir, scenarios, start_it, end_it):
    """Determine the set of features that are common across all scenarios."""
    global COMMON_FEATURES
    pcap_dir = os.path.join(base_dir, "packet_capture")
    scenario_features = {}

    # First, collect all features for each scenario
    for scenario, pattern in scenarios.items():
        print(f"\nScanning scenario: {scenario} to determine features...\n")
        scenario_features[scenario] = set()
        
        # Process first file of scenario to get initial feature set
        first_file = os.path.join(pcap_dir, f"{pattern}_it:{start_it}.pcap")
        if os.path.exists(first_file):
            try:
                features_df = extract_netml_features(first_file)
                scenario_features[scenario].update(features_df.columns)
            except Exception as e:
                print(f"Error processing file {first_file}: {e}")

    # Find common features across all scenarios
    COMMON_FEATURES = reduce(lambda x, y: x & y, scenario_features.values())
    print(f"Common features across all scenarios: {len(COMMON_FEATURES)}")
    return COMMON_FEATURES

def process_scenario_files(base_dir, scenario, pattern, start_it, end_it):
    """Process PCAP files and save extracted features as CSV files."""
    global COMMON_FEATURES

    pcap_dir = os.path.join(base_dir, "packet_capture")
    output_dir = os.path.join(base_dir, "session_Datasets", scenario)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i in range(start_it, end_it + 1):
        pcap_file = os.path.join(pcap_dir, f"{pattern}_it:{i}.pcap")
        csv_file = os.path.join(output_dir, f"{pattern}_it:{i}.csv")

        if os.path.exists(pcap_file):
            print(f"Processing file: {pcap_file}")
            try:
                features_df = extract_netml_features(pcap_file)
                
                # Keep only common features
                features_df = features_df[sorted(COMMON_FEATURES)]
                
                # Save to CSV
                features_df.to_csv(csv_file, index=False, header=True)
                print(f"Features saved to {csv_file}")

            except Exception as e:
                print(f"Error processing file {pcap_file}: {e}")
        else:
            print(f"File missing: {pcap_file}")

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

    # First pass: Determine the common features across all scenarios
    determine_common_features(base_dir, scenarios, start_iteration, end_iteration)

    # Second pass: Process each scenario and save features to CSV
    for scenario, pattern in scenarios.items():
        process_scenario_files(base_dir, scenario, pattern, start_iteration, end_iteration)

if __name__ == "__main__":
    main()