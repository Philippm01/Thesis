import pandas as pd
import glob
from sklearn.svm import OneClassSVM
from sklearn.impute import SimpleImputer
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

# Path to normal traffic dataset (all CSVs)
dataset_path = "/home/philipp/Documents/Thesis/session_Datasets/normal/*.csv"

# Load all normal CSV files
csv_files = glob.glob(dataset_path)

# Use only the first 80 files for training
training_files = csv_files[:80]

# Load CSV files into dataframes
dataframes = load_csv_files(training_files)

if not dataframes:
    raise ValueError("No objects to concatenate. Ensure the CSV files are present and readable.")

# Combine all normal NetML feature data into one dataset
df_normal = pd.concat(dataframes, ignore_index=True)

# Handle NaN values by imputing with the mean of each column
imputer = SimpleImputer(strategy='mean')
X_train = imputer.fit_transform(df_normal)

print(f"✅ Loaded {len(X_train)} normal NetML flow entries for training.")

# Train One-Class SVM on normal traffic
svm_model = OneClassSVM(kernel="rbf", gamma="auto", nu=0.05)  # nu controls sensitivity

print("🚀 Training One-Class SVM...")
svm_model.fit(X_train)

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Save trained model in the same directory as the script
model_path = os.path.join(script_dir, "one_class_svm_model.pkl")
imputer_path = os.path.join(script_dir, "imputer.pkl")

# Save both model and imputer
joblib.dump(svm_model, model_path)
joblib.dump(imputer, imputer_path)

print(f"✅ Model trained and saved at {model_path}")
print(f"✅ Imputer saved at {imputer_path}")
