import pandas as pd
import glob
import os
import json
import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report
from tqdm import tqdm

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

base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
scenarios = ["normal", "slowloris", "quicly", "lsquic"]

scenario_config = {
    "normal": {"label": 0, "prefix": None},
    "slowloris": {"label": 1, "prefix": "slowloris_isolated_con:5-10_sleep:1-5_time:100_it:"},
    "quicly": {"label": 2, "prefix": "quicly_isolation_time:100_it:"},
    "lsquic": {"label": 3, "prefix": "lsquic_isolation_time:100_it:"}
}

print("Loading datasets...")
dataframes = []
for scenario in scenarios:
    path = os.path.join(base_dir, scenario, "*.csv")
    csv_files = glob.glob(path)

    if scenario_config[scenario]["prefix"]:
        csv_files = [f for f in csv_files if os.path.basename(f).startswith(scenario_config[scenario]["prefix"])]

    dfs = load_csv_files(csv_files, scenario_config[scenario]["label"])
    dataframes.extend(dfs)

data = pd.concat(dataframes, ignore_index=True)

X = data.drop(columns=['label'])
y = data['label']

imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)
X_train, X_test, y_train, y_test = train_test_split(X_imputed, y, test_size=0.2, random_state=42, stratify=y)

param_grid = {
    'n_estimators': [100, 200, 300],
    'learning_rate': [0.01, 0.1, 0.2],
    'max_depth': [3, 6, 10],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4]
}

gb_clf = GradientBoostingClassifier(random_state=42)
grid_search = GridSearchCV(estimator=gb_clf, param_grid=param_grid,
                           cv=3, n_jobs=-1, verbose=2,
                           scoring='f1_macro')

print("\nStarting Grid Search...")
grid_search.fit(X_train, y_train)
print("Best parameters found:")
print(grid_search.best_params_)

print("\nEvaluating best model on test set...")
y_pred = grid_search.predict(X_test)
report = classification_report(y_test, y_pred,
                               target_names=['Normal', 'Slowloris', 'Quicly', 'LSQUIC'])
print("Classification Report:")
print(report)

model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gradient_boosting_model")
os.makedirs(model_dir, exist_ok=True)
model_path = os.path.join(model_dir, "gb_best_model.pkl")
imputer_path = os.path.join(model_dir, "imputer.pkl")
params_path = os.path.join(model_dir, "best_parameters.txt")

with open(params_path, 'w') as f:
    f.write("Best Gradient Boosting Parameters:\n")
    for param, value in grid_search.best_params_.items():
        f.write(f"{param}: {value}\n")

joblib.dump(grid_search.best_estimator_, model_path)
joblib.dump(imputer, imputer_path)

results = {
    "best_params": grid_search.best_params_,
    "classification_report": report
}

results_path = os.path.join(model_dir, "gb_results.json")
with open(results_path, 'w') as f:
    json.dump(results, f, indent=4)

print(f"\nModel and results saved to {model_dir}")
