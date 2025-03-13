import pandas as pd
import glob
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
import joblib
import os

def load_csv_files(file_paths):
    dataframes = []
    for file in file_paths:
        try:
            df = pd.read_csv(file)
            dataframes.append(df)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    return dataframes

dataset_path = "/home/philipp/Documents/Thesis/session_Datasets/normal/*.csv"
csv_files = glob.glob(dataset_path)
training_files = csv_files[:80]
dataframes = load_csv_files(training_files)

if not dataframes:
    raise ValueError("No objects to concatenate")

df_normal = pd.concat(dataframes, ignore_index=True)
imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(df_normal)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_imputed)

print(f"Loaded {len(X_train)} normal NetML flow entries for training")

iforest = IsolationForest(
    n_estimators=100,
    contamination=0.001,  # Similar to nu in OneClassSVM
    max_samples='auto',
    random_state=42
)
iforest.fit(X_train)

script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "isolation_forest_model.pkl")
imputer_path = os.path.join(script_dir, "imputer.pkl")
scaler_path = os.path.join(script_dir, "scaler.pkl")

joblib.dump(iforest, model_path)
joblib.dump(imputer, imputer_path)
joblib.dump(scaler, scaler_path)

print(f"Model trained and saved at {model_path}")
print(f"Imputer saved at {imputer_path}")
print(f"Scaler saved at {scaler_path}")
