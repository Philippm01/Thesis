import os
import pandas as pd
import numpy as np
from scipy.stats import mannwhitneyu
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import argparse
from tqdm import tqdm

def read_data(base_dir):
    data = {}
    scenarios = ["normal", "flood", "slowloris", "quicly", "lsquic"]
    for scenario in scenarios:
        scenario_path = os.path.join(base_dir, scenario)
        if not os.path.exists(scenario_path):
            print(f"Directory not found: {scenario_path}")
            continue
        
        csv_files = [f for f in glob.glob(os.path.join(scenario_path, "*.csv"))]
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
            print(f"No valid CSV files found in {scenario_path}")
    return data

def basic_stats(data):
    stats = {}
    for scenario, df in data.items():
        stats[scenario] = df.describe()
    return stats

def mann_whitney_test(normal_data, attack_data, feature):
    u, p = mannwhitneyu(normal_data[feature], attack_data[feature])
    return p

def feature_importance(data):
    importance = {}
    normal_df = data["normal"]
    for scenario in data:
        if scenario == "normal":
            continue
        attack_df = data[scenario]
        combined_df = pd.concat([normal_df, attack_df], ignore_index=True)
        combined_df["target"] = [0] * len(normal_df) + [1] * len(attack_df)
        
        X = combined_df.drop("target", axis=1)
        y = combined_df["target"]
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        model = RandomForestClassifier(random_state=42)
        model.fit(X_train, y_train)
        
        importance[scenario] = pd.Series(model.feature_importances_, index=X.columns)
    return importance

def main():
    parser = argparse.ArgumentParser(description='Analyze feature variance between normal and attack scenarios.')
    parser.add_argument('--data-dir', type=str, required=True, 
                        help='Path to the base directory containing scenario subdirectories.')
    args = parser.parse_args()

    base_dir = args.data_dir
    
    data = read_data(base_dir)
    if not data:
        print("No data to analyze.")
        return
    
    # Basic Statistics
    stats = basic_stats(data)
    for scenario, df in stats.items():
        print(f"\n{'='*20} {scenario.upper()} STATISTICS {'='*20}")
        print(df)
    
    # Statistical Tests (Mann-Whitney U test)
    print("\n{'='*20} MANN-WHITNEY U TESTS {'='*20}")
    normal_data = data["normal"]
    for scenario in data:
        if scenario == "normal":
            continue
        attack_data = data[scenario]
        print(f"\n{scenario.upper()} vs NORMAL:")
        p_values = {}
        for feature in tqdm(normal_data.columns, desc="Testing features"):
            try:
                p = mann_whitney_test(normal_data, attack_data, feature)
                p_values[feature] = p
            except Exception as e:
                print(f"Error testing feature {feature}: {e}")
                continue
        
        sorted_p_values = sorted(p_values.items(), key=lambda x: x[1])
        print("Top features by p-value:")
        for feature, p in sorted_p_values[:5]:
            print(f"  {feature}: {p}")
    
    # Feature Importance (Random Forest)
    print("\n{'='*20} FEATURE IMPORTANCE (RANDOM FOREST) {'='*20}")
    importances = feature_importance(data)
    for scenario, series in importances.items():
        print(f"\n{scenario.upper()}:")
        sorted_importances = series.sort_values(ascending=False)
        print(sorted_importances.head(5))

if __name__ == "__main__":
    main()
