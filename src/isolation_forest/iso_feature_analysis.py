import pandas as pd

# Load dataset with anomaly results
df = pd.read_csv("packet_level_anomaly_detection.csv")

# Ensure we only use numeric columns for analysis
df_anomalies = df[df["Anomaly"] == "attack"]

# Drop non-numeric columns
df_anomalies_numeric = df_anomalies.select_dtypes(include=['number'])  # Keep only numeric features

# Compute statistics for anomalies
anomaly_stats = df_anomalies_numeric.describe()

# Identify features where anomalies significantly differ from normal packets
anomaly_variance = df_anomalies_numeric.var()
sorted_variance = anomaly_variance.sort_values(ascending=False)  # Sort by highest variance

# Display top varying features in anomalies
print("\n🔍 Features with Highest Variation in Anomalous Packets:\n")
print(sorted_variance.head(10))

# Save results for deeper analysis
anomaly_stats.to_csv("anomalous_packet_statistics.csv")

