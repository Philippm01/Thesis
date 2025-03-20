import os
import pandas as pd
import numpy as np
import glob

def read_data(base_dir, file_prefixes):
    data = {}
    scenarios = ["normal", "slowloris", "quicly", "lsquic"]
    for scenario in scenarios:
        scenario_path = os.path.join(base_dir, scenario)
        if not os.path.exists(scenario_path):
            print(f"Directory not found: {scenario_path}")
            continue
        
        csv_files = [f for f in glob.glob(os.path.join(scenario_path, "*.csv"))]
        
        if scenario != "normal":
            prefix = file_prefixes.get(scenario)
            csv_files = [f for f in csv_files if prefix and os.path.basename(f).startswith(prefix)]
        
        dfs = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                dfs.append(df)
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")
        
        if dfs:
            data[scenario] = pd.concat(dfs, ignore_index=True)
        else:
            print(f"No valid CSV files found in {scenario_path} with specified prefix")
    return data

def calculate_stats(data):
    stats = {}
    for scenario, df in data.items():
        stats[scenario] = {
            "mean": df.mean(),
            "std": df.std()
        }
    return stats

def main():
    base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
    file_prefixes = {
        "slowloris": "slowloris_isolated_con:5-10_sleep:1-5_time:180",
        "quicly": "quicly_isolation_time:180",
        "lsquic": "lsquic_isolated_time:180"
    }
    
    data = read_data(base_dir, file_prefixes)
    if not data:
        print("No data to analyze.")
        return
    
    stats = calculate_stats(data)
    
    mean_df = pd.DataFrame({scenario: stat["mean"] for scenario, stat in stats.items()})
    std_df = pd.DataFrame({scenario: stat["std"] for scenario, stat in stats.items()})
    
    output_dir = os.path.dirname(os.path.abspath(__file__))
    mean_output_csv_path = os.path.join(output_dir, "feature_means.csv")
    std_output_csv_path = os.path.join(output_dir, "feature_std_devs.csv")
    
    mean_df.to_csv(mean_output_csv_path, index=True)
    std_df.to_csv(std_output_csv_path, index=True)
    
    print(f"Mean values saved to {mean_output_csv_path}")
    print(f"Standard deviations saved to {std_output_csv_path}")

    if "normal" in stats:
        normal_mean = stats["normal"]["mean"]
        normal_std = stats["normal"]["std"]
        
        mean_diffs = {scenario: stats[scenario]["mean"] - normal_mean for scenario in stats if scenario != "normal"}
        std_diffs = {scenario: stats[scenario]["std"] - normal_std for scenario in stats if scenario != "normal"}
        
        mean_diff_df = pd.DataFrame(mean_diffs)
        std_diff_df = pd.DataFrame(std_diffs)
        
        mean_diff_output_csv_path = os.path.join(output_dir, "feature_means_diff.csv")
        std_diff_output_csv_path = os.path.join(output_dir, "feature_std_devs_diff.csv")
        
        mean_diff_df.to_csv(mean_diff_output_csv_path, index=True)
        std_diff_df.to_csv(std_diff_output_csv_path, index=True)
        
        print(f"Mean differences saved to {mean_diff_output_csv_path}")
        print(f"Standard deviation differences saved to {std_diff_output_csv_path}")
    else:
        print("Normal data not found. Cannot calculate differences.")

if __name__ == "__main__":
    main()
