import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Load dataset
file_path = "../all_iterations_quic_packets.csv"  # Adjust if needed
df = pd.read_csv(file_path)

# Inspect dataset to check for missing values
print("\n🔍 Dataset Info Before Preprocessing:")
print(df.info())

# Drop Attack Type column (completely ignored for anomaly detection)
df_features = df.drop(columns=["Attack Type"], errors='ignore')  

# Convert all columns to numeric (force non-numeric values to NaN)
df_features = df_features.apply(pd.to_numeric, errors='coerce')

# Fill missing values (replace NaN with 0)
df_features = df_features.fillna(0)  

# Scale features to normalize impact
scaler = StandardScaler()
df_scaled = pd.DataFrame(scaler.fit_transform(df_features), columns=df_features.columns)

# Apply manually defined weights (strong emphasis on frame type and settings capacity)
feature_weights = {
    # General packet features
    "Packet Number": 1.0,
    "Packet Length": 1.0,
    "Interarrival Time": 1.0,
    "Num QUIC Frames": 1.0,
    "Num HTTP3 Frames": 1.0,

    # QUIC Frame details
    "QUIC_Frame_1_Type": 5.0,
    "QUIC_Frame_2_Type": 5.0,
    "QUIC_Frame_3_Type": 5.0,
    "QUIC_Frame_4_Type": 5.0,
    "QUIC_Frame_5_Type": 5.0,

    # HTTP3 Settings Capacity (Highly Weighted)
    "HTTP3_Frame_1_Settings_Capacity": 5.0,
    "HTTP3_Frame_2_Settings_Capacity": 5.0,
    "HTTP3_Frame_3_Settings_Capacity": 5.0,
    "HTTP3_Frame_4_Settings_Capacity": 5.0,
    "HTTP3_Frame_5_Settings_Capacity": 5.0,
}

# Apply feature weights (only to specified columns)
for col, weight in feature_weights.items():
    if col in df_scaled.columns:
        df_scaled[col] *= weight

# Check for NaN values before training
print("\n🔍 Checking for NaN values before training:")
print(df_scaled.isna().sum())  # Show NaN count for each column

# Train Isolation Forest (on entire dataset)
iso_forest = IsolationForest(contamination=0.01, random_state=42)  # 1% anomalies
iso_forest.fit(df_scaled)

# Predict anomalies on the entire dataset
df["Anomaly Score"] = iso_forest.decision_function(df_scaled)  # Higher = more normal
df["Anomaly"] = iso_forest.predict(df_scaled)  # -1 = Anomaly, 1 = Normal

# Convert -1 (anomaly) and 1 (normal) to readable labels
df["Anomaly"] = df["Anomaly"].map({1: "normal", -1: "attack"})

# Ensure "Anomaly" exists before filtering
if "Anomaly" in df.columns:
    df_normal = df[df["Anomaly"] == "normal"].copy()
else:
    print("❌ Warning: 'Anomaly' column not found. Skipping filtering step.")
    df_normal = df.copy()

# Save results
df.to_csv("packet_level_anomaly_detection.csv", index=False)

# Print detection summary
print(df["Anomaly"].value_counts())
