import pandas as pd
import glob
import os
import joblib
import json
import numpy as np
from sklearn.impute import SimpleImputer
import argparse
from tqdm import tqdm


# python3 benchmarking_ocsvm.py --model-path ocsvm/one_class_svm_model.pkl --normal-start 90 --normal-end 91 --attack-start 1 --attack-end 1


def test_scenario(scenario_path, model, imputer, scaler, scenario_name, normal_range, attack_range):
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
            # Load and transform data using both imputer and scaler
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
    parser = argparse.ArgumentParser(description='Test OCSVM model with custom ranges')
    parser.add_argument('--model-path', type=str, required=True, 
                       help='Path to model file relative to /home/philipp/Documents/Thesis/src')
    parser.add_argument('--normal-start', type=int, default=81)
    parser.add_argument('--normal-end', type=int, default=100)
    parser.add_argument('--attack-start', type=int, default=1)
    parser.add_argument('--attack-end', type=int, default=20)
    args = parser.parse_args()

    base_src_dir = "/home/philipp/Documents/Thesis/src"
    model_dir = os.path.dirname(os.path.join(base_src_dir, args.model_path))
    model_name = os.path.splitext(os.path.basename(args.model_path))[0]
    
    # Load model, imputer and scaler
    try:
        model = joblib.load(os.path.join(base_src_dir, args.model_path))
        imputer = joblib.load(os.path.join(model_dir, "imputer.pkl"))
        scaler = joblib.load(os.path.join(model_dir, "scaler.pkl"))
        print(f"Model and preprocessing components loaded successfully")
    except Exception as e:
        print(f"Error loading model components: {e}")
        return

    normal_range = (args.normal_start, args.normal_end)
    attack_range = (args.attack_start, args.attack_end)
    base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
    scenarios = ["normal", "flooding", "slowloris", "quicly", "lsquic"]
    
    all_results = {
        "scenarios": [],
        "test_ranges": {
            "normal": {"start": args.normal_start, "end": args.normal_end},
            "attack": {"start": args.attack_start, "end": args.attack_end}
        }
    }
    
    for scenario in scenarios:
        scenario_path = os.path.join(base_dir, scenario)
        if not os.path.exists(scenario_path):
            print(f"Directory of scenario not found: {scenario_path}")
            continue
            
        results = test_scenario(scenario_path, model, imputer, scaler, 
                              scenario, normal_range, attack_range)
        if results:
            all_results["scenarios"].append(results)
    
    # Save results
    results_file = f"{model_name}_test_results.json"
    results_path = os.path.join(model_dir, results_file)
    
    if os.path.exists(results_path):
        os.remove(results_path)
    
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=4)
    
    print(f"\nResults saved to {results_path}")

if __name__ == "__main__":
    main()
