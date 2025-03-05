from netml.pparser.parser import PCAP
import numpy as np
import pandas as pd

# Path to the pcap file
pcap_file = '/home/philipp/Documents/Thesis/packet_capture/flood_con:20-50_time:180_it:10.pcap'

# Initialize the PCAP parser
pcap = PCAP(pcap_file, flow_ptks_thres=2)
pcap.pcap2flows()

# Extract multiple feature types
feature_types = ['IAT', 'STATS', 'SIZE', 'SAMP_NUM', 'SAMP_SIZE']
extracted_data = []
actual_feature_names = []

for ft in feature_types:
    pcap.flow2features(ft, fft=False, header=True)
    data = pcap.features
    extracted_data.append(data)
    
    # Check if NetML provides feature names
    if hasattr(pcap, 'fieldnames'):
        actual_feature_names.extend(pcap.fieldnames)
    else:
        actual_feature_names.extend([f"{ft}_{i+1}" for i in range(data.shape[1])])

# Ensure all extracted feature arrays have the same number of rows
min_rows = min([data.shape[0] for data in extracted_data])
extracted_data = [data[:min_rows] for data in extracted_data]  # Trim to match row count

# Concatenate extracted features
combined_features = np.hstack(extracted_data)

# Convert extracted features into a DataFrame
df = pd.DataFrame(combined_features, columns=actual_feature_names)

# Save to CSV
df.to_csv("verified_extracted_features.csv", index=False)
print("Extracted features saved to verified_extracted_features.csv")

# Print actual feature names detected
print("Actual extracted feature names:\n", actual_feature_names)
