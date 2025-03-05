import pandas as pd
import glob
import os
from model_utils import load_models

def test_scenario(scenario_path, model, imputer):
    """Test all files in a scenario directory and return statistics."""
    csv_files = sorted(glob.glob(os.path.join(scenario_path, "*.csv")))
    total_normal = total_attack = total_flows = 0
    
    for file in csv_files[80:100]:  # Test files 81-100
        df = pd.read_csv(file)
        X = imputer.transform(df)
        predictions = model.predict(X)
        
        normal = sum(predictions == 1)
        attack = sum(predictions == -1)
        
        print(f"\n{os.path.basename(file)}:")
        print(f"Normal: {normal}, Attack: {attack} (Total: {len(predictions)})")
        
        total_normal += normal
        total_attack += attack
        total_flows += len(predictions)
    
    return total_normal, total_attack, total_flows

def main():
    # Load the model and imputer
    model, imputer = load_models()
    if not model or not imputer:
        return

    base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
    scenarios = ["normal", "flooding", "slowloris", "quicly", "lsquic"]
    
    for scenario in scenarios:
        print(f"\n{'='*20} {scenario.upper()} {'='*20}")
        scenario_path = os.path.join(base_dir, scenario)
        
        normal, attack, total = test_scenario(scenario_path, model, imputer)
        
        print(f"\nSummary for {scenario}:")
        print(f"Normal flows: {normal}/{total} ({normal/total*100:.1f}%)")
        print(f"Attack flows: {attack}/{total} ({attack/total*100:.1f}%)")

if __name__ == "__main__":
    main()
