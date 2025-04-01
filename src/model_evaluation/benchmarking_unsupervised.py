import pandas as pd
import glob
import joblib
import os
import argparse
from collections import Counter

parser = argparse.ArgumentParser(description="...")
parser.add_argument('--model_dir', type=str, required=True, help="P...")
args = parser.parse_args()

model = joblib.load(os.path.join(args.model_dir, "...pkl"))
imputer = joblib.load(os.path.join(args.model_dir, "imputer.pkl"))
scaler = joblib.load(os.path.join(args.model_dir, "scaler.pkl"))

scenario_config = {
    "normal": {"label": 0, "prefix": None},
    "flood": {"label": 1, "prefix": None},  
    "slowloris": {"label": 1, "prefix": "slowloris_isolated_con:5-10_sleep:1-5_time:100_it:"},
    "quicly": {"label": 2, "prefix": "quicly_isolation_time:100_it:"},
    "lsquic": {"label": 3, "prefix": "lsquic_isolation_time:100_it:"}
}

def summarize_predictions(scenario_config, base_path):
    summaries = {}

    for scenario, config in scenario_config.items():
        prefix = config['prefix']
        pattern = f"**/{prefix}*.csv" if prefix else "**/*.csv"
        file_paths = glob.glob(os.path.join(base_path, pattern), recursive=True)
        if scenario == "normal":
            file_paths = [f for f in file_paths if "it:" in f and 81 <= int(f.split("it:")[1].split(".")[0]) <= 100]

        if not file_paths:
            print(f"No files found for scenario '{scenario}'")
            continue

        dfs = [pd.read_csv(file) for file in file_paths]
        data = pd.concat(dfs, ignore_index=True)

        X_test = scaler.transform(imputer.transform(data))
        predictions = model.predict(X_test)

        pred_counts = Counter(predictions)
        total_predictions = sum(pred_counts.values())
        attack_percentage = (pred_counts.get(-1, 0) / total_predictions) * 100
        normal_percentage = (pred_counts.get(1, 0) / total_predictions) * 100

        summaries[scenario] = {
            "attack_percentage": attack_percentage,
            "normal_percentage": normal_percentage
        }

        print(f"Scenario '{scenario}':")
        print(f"  Attack Percentage: {attack_percentage:.2f}%")
        print(f"  Normal Percentage: {normal_percentage:.2f}%")

    return summaries

base_dataset_path = "/home/philipp/Documents/Thesis/session_Datasets"

summarize_predictions(scenario_config, base_dataset_path)