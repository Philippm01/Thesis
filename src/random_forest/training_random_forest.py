import pandas as pd
import glob
import os
import json
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from joblib import parallel_backend

# Configurations
base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
scenarios = ["normal", "slowloris", "quicly", "lsquic"]
scenario_config = {
    "normal": {"label": 0, "prefix": None},
    "slowloris": {"label": 1, "prefix": "slowloris_isolated_con:5-10_sleep:1-5_time:100_it:"},
    "quicly": {"label": 2, "prefix": "quicly_isolation_time:100_it:"},
    "lsquic": {"label": 3, "prefix": "lsquic_isolation_time:100_it:"}
}

# Load function
def load_csv_files(file_paths, label):
    dfs = []
    for file in file_paths:
        try:
            df = pd.read_csv(file)
            df['label'] = label
            dfs.append(df)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    return dfs

# Load and concatenate all data
print("Loading datasets...")
dataframes = []
for scenario in scenarios:
    path = os.path.join(base_dir, scenario, "*.csv")
    csv_files = glob.glob(path)

    prefix = scenario_config[scenario]["prefix"]
    if prefix:
        csv_files = [f for f in csv_files if os.path.basename(f).startswith(prefix)]

    dfs = load_csv_files(csv_files, scenario_config[scenario]["label"])
    dataframes.extend(dfs)

data = pd.concat(dataframes, ignore_index=True)

# Split features and labels
X = data.drop(columns=['label'])
y = data['label']

# Preprocess with imputation
imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)
X_train, X_test, y_train, y_test = train_test_split(
    X_imputed, y, test_size=0.2, random_state=42, stratify=y
)

# Train using the best found parameters
best_params = {
    'n_estimators': 722,
    'max_depth': 50,
    'min_samples_split': 2,
    'min_samples_leaf': 1,
    'class_weight': 'balanced_subsample'
}

print("Training RandomForest with best parameters...")
model = RandomForestClassifier(**best_params, n_jobs=-1, random_state=42)
with parallel_backend('loky'):
    model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
report = classification_report(y_test, y_pred, target_names=['Normal', 'Slowloris', 'Quicly', 'LSQUIC'])
print("Classification Report:\n", report)

# Save model and results
model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "random_forest_model")
os.makedirs(model_dir, exist_ok=True)
joblib.dump(model, os.path.join(model_dir, "random_forest_best_model.pkl"))
joblib.dump(imputer, os.path.join(model_dir, "imputer.pkl"))

results = {
    "best_params": best_params,
    "classification_report": report
}
with open(os.path.join(model_dir, "rf_results.json"), "w") as f:
    json.dump(results, f, indent=4)

print(f"\nModel and results saved to {model_dir}")
import pandas as pd
import glob
import os
import json
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from joblib import parallel_backend

# Configurations
base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
scenarios = ["normal", "slowloris", "quicly", "lsquic"]
scenario_config = {
    "normal": {"label": 0, "prefix": None},
    "slowloris": {"label": 1, "prefix": "slowloris_isolated_con:5-10_sleep:1-5_time:100_it:"},
    "quicly": {"label": 2, "prefix": "quicly_isolation_time:100_it:"},
    "lsquic": {"label": 3, "prefix": "lsquic_isolation_time:100_it:"}
}

# Load function
def load_csv_files(file_paths, label):
    dfs = []
    for file in file_paths:
        try:
            df = pd.read_csv(file)
            df['label'] = label
            dfs.append(df)
        except Exception as e:
            print(f"Error loading {file}: {e}")
    return dfs

# Load and concatenate all data
print("Loading datasets...")
dataframes = []
for scenario in scenarios:
    path = os.path.join(base_dir, scenario, "*.csv")
    csv_files = glob.glob(path)

    prefix = scenario_config[scenario]["prefix"]
    if prefix:
        csv_files = [f for f in csv_files if os.path.basename(f).startswith(prefix)]

    dfs = load_csv_files(csv_files, scenario_config[scenario]["label"])
    dataframes.extend(dfs)

data = pd.concat(dataframes, ignore_index=True)

# Split features and labels
X = data.drop(columns=['label'])
y = data['label']

# Preprocess with imputation
imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)
X_train, X_test, y_train, y_test = train_test_split(
    X_imputed, y, test_size=0.2, random_state=42, stratify=y
)

# Train using the best found parameters
best_params = {
    'n_estimators': 722,
    'max_depth': 50,
    'min_samples_split': 2,
    'min_samples_leaf': 1,
    'class_weight': 'balanced_subsample'
}

print("Training RandomForest with best parameters...")
model = RandomForestClassifier(**best_params, n_jobs=-1, random_state=42)
with parallel_backend('loky'):
    model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
report = classification_report(y_test, y_pred, target_names=['Normal', 'Slowloris', 'Quicly', 'LSQUIC'])
print("Classification Report:\n", report)

# Save model and results
model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "random_forest_model")
os.makedirs(model_dir, exist_ok=True)
joblib.dump(model, os.path.join(model_dir, "random_forest_best_model.pkl"))
joblib.dump(imputer, os.path.join(model_dir, "imputer.pkl"))

results = {
    "best_params": best_params,
    "classification_report": report
}
with open(os.path.join(model_dir, "rf_results.json"), "w") as f:
    json.dump(results, f, indent=4)

print(f"\nModel and results saved to {model_dir}")