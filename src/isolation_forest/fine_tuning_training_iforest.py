import pandas as pd
import glob
from sklearn.ensemble import IsolationForest  # Add this import
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import joblib
import os
from itertools import product
import json
from tqdm import tqdm

def load_csv_files(file_paths):
    dataframes = []
    for file in file_paths:
        try:
            df = pd.read_csv(file)
            dataframes.append(df)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    return dataframes

def test_scenario(scenario_path, model, scaler, imputer, scenario_name):
    csv_files = glob.glob(os.path.join(scenario_path, "*.csv"))
    
    file_numbers = []
    for f in csv_files:
        try:
            num = int(f.split('it:')[1].split('.')[0])
            file_numbers.append((f, num))
        except:
            continue
    
    file_numbers.sort(key=lambda x: x[1])
    valid_files = [f for f, num in file_numbers if 1 <= num <= 50]
    
    if not valid_files:
        return None

    results = {
        "scenario": scenario_name,
        "files": [],
        "total": {"normal": 0, "attack": 0, "total": 0}
    }
    
    for file in tqdm(valid_files, desc=f"Testing {scenario_name}"):
        try:
            df = pd.read_csv(file)
            X = imputer.fit_transform(df)
            if scaler is not None:
                X = scaler.transform(X)
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

contamination_values = [0.0001, 0.001, 0.01, 0.05, 0.1, 0.2]
n_estimators_values = [100, 200, 500, 1000]
max_samples_values = [10000] 
scaling_methods = [
    ('none', None),
    ('standard', StandardScaler()),
    ('minmax', MinMaxScaler())
]

dataset_path = "/home/philipp/Documents/Thesis/session_Datasets/normal/*.csv"
csv_files = glob.glob(dataset_path)
training_files = csv_files[:10]
print(f"Using {len(training_files)} files for training")

dataframes = load_csv_files(training_files)
if not dataframes:
    raise ValueError("No objects to concatenate")

df_normal = pd.concat(dataframes, ignore_index=True)
imputer = SimpleImputer(strategy='mean')
X_train = imputer.fit_transform(df_normal)

print(f"Loaded {len(X_train)} normal NetML flow entries for training")

script_dir = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(script_dir, "grid_search_models")
os.makedirs(models_dir, exist_ok=True)

all_results = {
    "training_info": {
        "samples": len(X_train),
        "files_used": len(training_files)
    },
    "models": []
}

for cont, n_est, max_samp, (scaling_name, scaler) in product(
    contamination_values, n_estimators_values, 
    max_samples_values, scaling_methods):
    
    model_name = f"iforest_cont{cont}_est{n_est}_samp{max_samp}_{scaling_name}".replace(".", "")
    print(f"\nTraining model: {model_name}")
    print(f"Parameters: contamination={cont}, n_estimators={n_est}, "
          f"max_samples={max_samp}, scaling={scaling_name}")
    
    X_train_scaled = X_train
    if scaler is not None:
        X_train_scaled = scaler.fit_transform(X_train)
    
    iforest = IsolationForest(
        contamination=cont,
        n_estimators=n_est,
        max_samples=max_samp,
        random_state=42
    )
    iforest.fit(X_train_scaled)
    
    model_path = os.path.join(models_dir, f"{model_name}.pkl")
    imputer_path = os.path.join(models_dir, f"{model_name}_imputer.pkl")
    
    joblib.dump(iforest, model_path)
    joblib.dump(imputer, imputer_path)
    
    if scaler is not None:
        scaler_path = os.path.join(models_dir, f"{model_name}_scaler.pkl")
        joblib.dump(scaler, scaler_path)

    base_dir = "/home/philipp/Documents/Thesis"
    scenarios = ["normal", "flooding", "slowloris", "quicly", "lsquic"]
    
    model_results = {
        "model_name": model_name,
        "parameters": {
            "contamination": cont,
            "n_estimators": n_est,
            "max_samples": max_samp,
            "scaling": scaling_name
        },
        "scenarios": []
    }
    
    for scenario in scenarios:
        scenario_path = os.path.join(base_dir, "session_Datasets", scenario)
        if os.path.exists(scenario_path):
            results = test_scenario(scenario_path, iforest, scaler, imputer, scenario)
            if results:
                model_results["scenarios"].append(results)
    
    all_results["models"].append(model_results)
    
    print(f"Model complete: {model_name}")
    for scenario in model_results["scenarios"]:
        print(f"{scenario['scenario']}: Normal={scenario['total']['normal_percentage']:.2f}%, "
              f"Attack={scenario['total']['attack_percentage']:.2f}%")

results_file = os.path.join(script_dir, "complete_grid_search_results.json")
with open(results_file, 'w') as f:
    json.dump(all_results, f, indent=4)

print(f"\nAll results saved to {results_file}")
print(f"Models saved in: {models_dir}")
