import pandas as pd
import glob
from sklearn.svm import OneClassSVM
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
import joblib
import os
import numpy as np

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
X_scaled = scaler.fit_transform(X_imputed)


svm_model = OneClassSVM(kernel="rbf", gamma="auto", nu=0.01)
svm_model.fit(X_scaled)


script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "one_class_svm_model.pkl")
imputer_path = os.path.join(script_dir, "imputer.pkl")
scaler_path = os.path.join(script_dir, "scaler.pkl")

joblib.dump(svm_model, model_path)
joblib.dump(imputer, imputer_path)
joblib.dump(scaler, scaler_path)

print(f"Weighted Model trained and saved at {model_path}")
print(f"Imputer saved at {imputer_path}")
print(f"Scaler saved at {scaler_path}")
