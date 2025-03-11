import pandas as pd
import glob
from sklearn.svm import OneClassSVM
from sklearn.impute import SimpleImputer
import joblib
import os
from itertools import product

def load_csv_files(file_paths):
    dataframes = []
    for file in file_paths:
        try:
            df = pd.read_csv(file)
            dataframes.append(df)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    return dataframes

# Hyperparameter grid
nu_values = [0.01, 0.02, 0.05, 0.1]
gamma_values = ['scale', 'auto', 0.001, 0.0001]

# Path to normal traffic dataset
dataset_path = "/home/philipp/Documents/Thesis/session_Datasets/normal/*.csv"
csv_files = glob.glob(dataset_path)

# Use only 10 files for training
training_files = csv_files[:10]
print(f"Using {len(training_files)} files for training")

# Load and prepare data
dataframes = load_csv_files(training_files)
if not dataframes:
    raise ValueError("No objects to concatenate")

df_normal = pd.concat(dataframes, ignore_index=True)
imputer = SimpleImputer(strategy='mean')
X_train = imputer.fit_transform(df_normal)

print(f"Loaded {len(X_train)} normal NetML flow entries for training")

# Create output directory for models
script_dir = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(script_dir, "grid_search_models")
os.makedirs(models_dir, exist_ok=True)

# Train models with different hyperparameters
for nu, gamma in product(nu_values, gamma_values):
    model_name = f"ocsvm_nu{nu}_gamma{gamma}".replace(".", "")
    print(f"\nTraining model: {model_name}")
    print(f"Parameters: nu={nu}, gamma={gamma}")
    
    svm_model = OneClassSVM(kernel="rbf", gamma=gamma, nu=nu)
    svm_model.fit(X_train)
    
    # Save model and imputer
    model_path = os.path.join(models_dir, f"{model_name}.pkl")
    imputer_path = os.path.join(models_dir, f"{model_name}_imputer.pkl")
    
    joblib.dump(svm_model, model_path)
    joblib.dump(imputer, imputer_path)
    
    print(f"✅ Saved model: {model_path}")

print("\nCompleted training all model variations")
print(f"Models saved in: {models_dir}")

# Save configuration summary
with open(os.path.join(models_dir, "models_info.txt"), "w") as f:
    f.write("One-Class SVM Models Training Summary\n")
    f.write("================================\n\n")
    f.write(f"Training samples: {len(X_train)}\n")
    f.write(f"Training files used: {len(training_files)}\n\n")
    f.write("Models created:\n")
    for nu, gamma in product(nu_values, gamma_values):
        f.write(f"\n- nu={nu}, gamma={gamma}")
        f.write(f"\n  Model name: ocsvm_nu{nu}_gamma{gamma}".replace(".", ""))
