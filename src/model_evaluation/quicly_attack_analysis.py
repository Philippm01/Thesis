import pandas as pd
import glob
import os
import joblib
import json
import numpy as np
from sklearn.impute import SimpleImputer
import argparse
from tqdm import tqdm
import matplotlib.pyplot as plt
import re

def test_scenario(scenario_path, model, imputer, scaler, scenario_name):
    print(f"\n{'='*20} {scenario_name.upper()} {'='*20}")
    
    csv_files = glob.glob(os.path.join(scenario_path, "*.csv"))
    
    valid_files = [f for f in csv_files if os.path.basename(f).startswith("quicly_attacks")]
    
    if not valid_files:
        return None

    print(f"Processing {len(valid_files)} files...")
    
    results = {
        "scenario": scenario_name,
        "files": [],
        "total": {"normal": 0, "attack": 0, "total": 0}
    }
    
    attack_percentages = {}
    
    for file in tqdm(valid_files, desc=f"Processing {scenario_name}"):
        try:
            # Extract number of attacks from filename using regex
            filename = os.path.basename(file)
            match = re.search(r'quicly_attacks:(\d+)_time', filename)
            if match:
                num_attacks = int(match.group(1))
            else:
                print(f"Could not extract number of attacks from filename: {filename}")
                continue
            
            # Load and transform data using both imputer and scaler
            df = pd.read_csv(file)
            X_imputed = imputer.transform(df)
            X = scaler.transform(X_imputed)
            
            predictions = model.predict(X)
            normal = int(sum(predictions == 1))
            attack = int(sum(predictions == -1))
            total = len(predictions)
            
            attack_percentage = float(attack/total*100)
            
            if num_attacks not in attack_percentages:
                attack_percentages[num_attacks] = []
            attack_percentages[num_attacks].append(attack_percentage)
            
            file_result = {
                "filename": os.path.basename(file),
                "normal": normal,
                "attack": attack,
                "total": total,
                "normal_percentage": float(normal/total*100),
                "attack_percentage": attack_percentage
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
    
    return attack_percentages

def main():
    parser = argparse.ArgumentParser(description='Test OCSVM model with custom ranges')
    parser.add_argument('--model-path', type=str, required=True, 
                       help='Path to model file relative to /home/philipp/Documents/Thesis/src')
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

    base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
    scenario = "quicly"
    scenario_path = os.path.join(base_dir, scenario)
    
    if not os.path.exists(scenario_path):
        print(f"Directory of scenario not found: {scenario_path}")
        return
            
    attack_percentages = test_scenario(scenario_path, model, imputer, scaler, 
                              scenario)
    
    if attack_percentages:
        # Calculate average attack percentage for each attack level
        avg_attack_percentages = {
            num_attacks: np.mean(percentages)
            for num_attacks, percentages in attack_percentages.items()
        }
        
        # Prepare data for plotting
        num_attacks_list = sorted(avg_attack_percentages.keys())
        avg_percentages_list = [avg_attack_percentages[k] for k in num_attacks_list]
        
        # Generate plot
        plt.figure(figsize=(10, 6))
        plt.plot(num_attacks_list, avg_percentages_list, marker='o')
        plt.title('Average Attack Percentage vs. Number of Attacks (Quicly)')
        plt.xlabel('Number of Attacks')
        plt.ylabel('Average Attack Percentage')
        plt.grid(True)
        
        # Save plot
        plot_file = f"{model_name}_quicly_attack_plot.png"
        plot_path = os.path.join(model_dir, plot_file)
        plt.savefig(plot_path)
        plt.close()
        
        print(f"\nPlot saved to {plot_path}")
    else:
        print("No results to plot.")

if __name__ == "__main__":
    main()
