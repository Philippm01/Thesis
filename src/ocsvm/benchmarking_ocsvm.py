import pandas as pd
import glob
import os
import joblib

def test_scenario(scenario_path, model, imputer, scenario_name):
    """Test files 81-100 from a scenario."""
    print(f"\n{'='*20} {scenario_name.upper()} {'='*20}")
    
    # Debug: Print the glob pattern being used
    glob_pattern = os.path.join(scenario_path, "*.csv")
    print(f"Looking for files in: {glob_pattern}")
    
    csv_files = sorted(glob.glob(glob_pattern))
    if not csv_files:
        print(f"⚠️  No CSV files found for scenario {scenario_name}")
        return
    
    # Debug: Print total files found
    print(f"Found {len(csv_files)} total files")
    test_files = csv_files[80:100]
    print(f"Using {len(test_files)} files for testing (81-100)")
    
    total_normal = total_attack = total_flows = 0
    
    for file in test_files:
        try:
            # Process file
            df = pd.read_csv(file)
            X = imputer.transform(df)
            predictions = model.predict(X)
            
            normal = sum(predictions == 1)
            attack = sum(predictions == -1)
            total = len(predictions)
            
            print(f"\n{os.path.basename(file)}:")
            print(f"Normal: {normal}/{total} ({normal/total*100:.1f}%)")
            print(f"Attack: {attack}/{total} ({attack/total*100:.1f}%)")
            
            total_normal += normal
            total_attack += attack
            total_flows += total
            
        except Exception as e:
            print(f"Error processing {file}: {e}")
    
    if total_flows > 0:
        print(f"\nOverall {scenario_name}:")
        print(f"Normal: {total_normal}/{total_flows} ({total_normal/total_flows*100:.1f}%)")
        print(f"Attack: {total_attack}/{total_flows} ({total_attack/total_flows*100:.1f}%)")

def main():
    # Get the current script's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load existing model and imputer
    try:
        model = joblib.load(os.path.join(current_dir, "one_class_svm_model.pkl"))
        imputer = joblib.load(os.path.join(current_dir, "imputer.pkl"))
        print("✅ Model and imputer loaded successfully")
    except Exception as e:
        print(f"Error loading model files: {e}")
        return

    base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
    scenarios = ["normal", "flooding", "slowloris", "quicly", "lsquic"]
    
    # Test each scenario and verify directory exists
    for scenario in scenarios:
        scenario_path = os.path.join(base_dir, scenario)
        if not os.path.exists(scenario_path):
            print(f"Directory not found: {scenario_path}")
            continue
        test_scenario(scenario_path, model, imputer, scenario)

if __name__ == "__main__":
    main()
