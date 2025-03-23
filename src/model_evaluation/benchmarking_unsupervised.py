import pandas as pd
import glob
import os
import joblib
import json
import numpy as np
from sklearn.impute import SimpleImputer
import argparse
from tqdm import tqdm

def test_scenario(scenario_path, model, imputer, scaler, scenario_name, normal_range, attack_range, file_prefix=None):
    print(f"\n{'='*20} {scenario_name.upper()} {'='*20}")
    
    csv_files = glob.glob(os.path.join(scenario_path, "*.csv"))
    
    file_numbers = []
    for f in csv_files:
        try:
            num = int(f.split('it:')[1].split('.')[0])
        except:
            num = -1
        file_numbers.append((f, num))
    
    file_numbers.sort(key=lambda x: x[1])
    
    if scenario_name == "normal":
        start, end = normal_range
        valid_files = [f for f, num in file_numbers if start <= num <= end]
    else:
        start, end = attack_range
        valid_files = [f for f, num in file_numbers if start <= num <= end]

    if file_prefix:
        valid_files = [f for f in valid_files if os.path.basename(f).startswith(file_prefix)]
    
    if not valid_files:
        return None

    print(f"Processing {len(valid_files)} files...")
    
    results = {
        "scenario": scenario_name,
        "files": [],
        "total": {"normal": 0, "attack": 0, "total": 0}
    }
    
    for file in tqdm(valid_files, desc=f"Processing {scenario_name}"):
        try:
            df = pd.read_csv(file)
            X_imputed = imputer.transform(df)
            X = scaler.transform(X_imputed)
            
            predictions = model.predict(X)
            normal = int(sum(predictions == 1))
            attack = int(sum(predictions == -1))
            total = len(predictions)
            
            file_result = {
                "filename": os.path.basename(file),
                "normal": normal,
                "attack": attack,
                "total": total,
                "normal_percentage": float(normal/total*100),
                "attack_percentage": float(attack/total*100)
            }
            
            results["files"].append(file_result)
            results["total"]["normal"] += normal
            results["total"]["attack"] += attack
            results["total"]["total"] += total
            
        except Exception as e:
            print(f"\nError processing {file}: {e}")
    
    if results["total"]["total"] > 0:
        total = results["total"]["total"]
        results["total"]["normal_percentage"] = float(results["total"]["normal"]/total*100)
        results["total"]["attack_percentage"] = float(results["total"]["attack"]/total*100)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Test models')
    parser.add_argument('--model-path', type=str, required=True, 
                       help='Path to model file relative to /home/philipp/Documents/Thesis/src')
    args = parser.parse_args()

    model_dir = os.path.dirname(args.model_path)
    model_name = os.path.splitext(os.path.basename(args.model_path))[0]

    try:
        model = joblib.load(args.model_path)
        imputer = joblib.load(os.path.join(model_dir, "imputer.pkl"))
        scaler = joblib.load(os.path.join(model_dir, "scaler.pkl"))
        print(f"Model loaded successfully")
    except Exception as e:
        print(f"Error loading model components: {e}")
        return

    normal_range = (81, 100)
    attack_range = (1, 20)
    base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
    scenarios = ["normal", "flood", "slowloris", "quicly", "lsquic"]
    
    all_results = {
        "scenarios": [],
        "test_ranges": {
            "normal": {"start": 81, "end": 100},
            "attack": {"start": 1, "end": 20}
        }
    }
    
    for scenario in scenarios:
        scenario_path = os.path.join(base_dir, scenario)
        if not os.path.exists(scenario_path):
            print(f"scenario not found: {scenario_path}")
            continue
        
        file_prefix = None
        if scenario == "slowloris":
            file_prefix = "slowloris_isolated_con:5-10_sleep:1-5_time:180"
        elif scenario == "quicly":
            file_prefix = "quicly_isolation"
        elif scenario == "lsquic":
            file_prefix = "lsquic_isolation"
            
        results = test_scenario(scenario_path, model, imputer, scaler, 
                              scenario, normal_range, attack_range, file_prefix)
        if results:
            all_results["scenarios"].append(results)
            print(f"\n{scenario.upper()} SUMMARY:")
            print(f"  Normal Percentage: {results['total']['normal_percentage']:.2f}%")
            print(f"  Attack Percentage: {results['total']['attack_percentage']:.2f}%")
    
    results_file = f"{model_name}_test_results.json"
    results_path = os.path.join(model_dir, results_file)
    
    if os.path.exists(results_path):
        os.remove(results_path)
    
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=4)
    
    print(f"\nResult saved to {results_path}")

if __name__ == "__main__":
    main()
