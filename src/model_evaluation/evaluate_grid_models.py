import pandas as pd
import glob
import os
import joblib
import json
import numpy as np
from sklearn.impute import SimpleImputer
import argparse
from tqdm import tqdm
from datetime import datetime

def test_scenario(scenario_path, model, scenario_name, training_mode=False):
    csv_files = glob.glob(os.path.join(scenario_path, "*.csv"))
    
    file_numbers = []
    for f in csv_files:
        try:
            num = int(f.split('it:')[1].split('.')[0])
            file_numbers.append((f, num))
        except:
            continue
    
    file_numbers.sort(key=lambda x: x[1])
    
    # Select files based on scenario and mode
    if scenario_name == "normal":
        if training_mode:
            valid_files = [f for f, num in file_numbers if 1 <= num <= 50]
        else:
            valid_files = [f for f, num in file_numbers if num > 50]
    else:
        if training_mode:
            return None  # No training for attack scenarios
        valid_files = [f for f, num in file_numbers if 1 <= num <= 50]
    
    if not valid_files:
        return None

    results = {
        "scenario": scenario_name,
        "mode": "training" if training_mode else "testing",
        "files": [],
        "total": {"normal": 0, "attack": 0, "total": 0}
    }
    
    imputer = SimpleImputer(strategy='mean')
    
    for file in tqdm(valid_files, desc=f"Processing {scenario_name}"):
        try:
            df = pd.read_csv(file)
            X = imputer.fit_transform(df)
            predictions = model.predict(X)
            
            normal = int(sum(predictions == 1))
            attack = int(sum(predictions == -1))
            total = len(predictions)
            
            results["files"].append({
                "filename": os.path.basename(file),
                "normal": normal,
                "attack": attack,
                "total": total,
                "normal_percentage": float(normal/total*100),
                "attack_percentage": float(attack/total*100)
            })
            
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
    parser = argparse.ArgumentParser(description='Evaluate grid search models')
    parser.add_argument('--models-dir', type=str, required=True,
                       help='Directory containing models relative to source directory')
    args = parser.parse_args()

    # Fix path handling
    base_dir = "/home/philipp/Documents/Thesis"
    base_src_dir = os.path.join(base_dir, "src")
    # Remove leading slash from models-dir if present
    models_dir_clean = args.models_dir.lstrip('/')
    models_dir = os.path.join(base_src_dir, models_dir_clean)
    
    # Verify directory exists
    if not os.path.exists(models_dir):
        raise ValueError(f"Models directory not found: {models_dir}")
    
    # Get all model files
    model_files = glob.glob(os.path.join(models_dir, "*.pkl"))
    model_files = [f for f in model_files if "imputer" not in f]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(models_dir, f"evaluation_results_{timestamp}.txt")
    
    scenarios = ["normal", "flooding", "slowloris", "quicly", "lsquic"]
    
    with open(log_file, 'w') as f:
        f.write("Grid Search Models Evaluation\n")
        f.write("==========================\n\n")
        f.write(f"Evaluation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for model_file in model_files:
            model_name = os.path.basename(model_file)
            print(f"\nEvaluating {model_name}")
            f.write(f"\nModel: {model_name}\n")
            f.write("=" * (len(model_name) + 7) + "\n")
            
            try:
                model = joblib.load(model_file)
                all_results = {"scenarios": []}
                
                for scenario in scenarios:
                    scenario_path = os.path.join(base_dir, "session_Datasets", scenario)
                    if not os.path.exists(scenario_path):
                        continue
                    
                    results = test_scenario(scenario_path, model, scenario, False)
                    if results:
                        all_results["scenarios"].append(results)
                        
                        f.write(f"\n{scenario.upper()}\n")
                        f.write(f"Total streams: {results['total']['total']}\n")
                        f.write(f"Normal: {results['total']['normal']} ")
                        f.write(f"({results['total']['normal_percentage']:.2f}%)\n")
                        f.write(f"Attack: {results['total']['attack']} ")
                        f.write(f"({results['total']['attack_percentage']:.2f}%)\n")
                
                # Save detailed JSON results
                json_file = os.path.join(models_dir, f"{model_name}_evaluation.json")
                with open(json_file, 'w') as jf:
                    json.dump(all_results, jf, indent=4)
                
            except Exception as e:
                print(f"Error evaluating {model_name}: {e}")
                f.write(f"\nError evaluating model: {e}\n")
            
            f.write("\n" + "-"*50 + "\n")
    
    print(f"\nEvaluation complete. Results saved to {log_file}")

if __name__ == "__main__":
    main()
