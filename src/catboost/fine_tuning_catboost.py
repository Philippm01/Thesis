import pandas as pd
import glob
import os
import json
import joblib
import optuna
import gc
from catboost import CatBoostClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report

base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
scenarios = ["normal", "slowloris", "quicly", "lsquic"]
scenario_config = {
    "normal": {"label": 0, "prefix": None},
    "slowloris": {"label": 1, "prefix": "slowloris_isolated_con:5-10_sleep:1-5_time:100_it:"},
    "quicly": {"label": 2, "prefix": "quicly_isolation_time:100_it:"},
    "lsquic": {"label": 3, "prefix": "lsquic_isolation_time:100_it:"}
}

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

print("Loading datasets...")
dataframes = []
for scenario in scenarios:
    path = os.path.join(base_dir, scenario, "*.csv")
    csv_files = glob.glob(path)

    if scenario_config[scenario]["prefix"]:
        csv_files = [f for f in csv_files if os.path.basename(f).startswith(scenario_config[scenario]["prefix"])]

    dataframes.extend(load_csv_files(csv_files, scenario_config[scenario]["label"]))

data = pd.concat(dataframes, ignore_index=True)
X = data.drop(columns=['label'])
y = data['label']

imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)
X_train, X_test, y_train, y_test = train_test_split(
    X_imputed, y, test_size=0.2, stratify=y, random_state=42
)

def objective(trial):
    params = {
        'iterations': trial.suggest_int('iterations', 100, 500),
        'depth': trial.suggest_int('depth', 4, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 1.0, 10.0),
        'random_strength': trial.suggest_float('random_strength', 0.0, 1.0),
        'bootstrap_type': trial.suggest_categorical('bootstrap_type', ['Bayesian', 'Bernoulli', 'MVS']),
        'loss_function': 'MultiClass',
        'verbose': 0,
        'random_seed': 42
    }

    model = CatBoostClassifier(**params)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test).reshape(-1)
    return f1_score(y_test, y_pred, average='macro')

print("\nStarting Bayesian Search...")
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=100, n_jobs=1)

print("\nBest parameters found:")
print(study.best_params)

print("\nEvaluating best model on test set...")
best_model = CatBoostClassifier(
    **study.best_params,
    loss_function='MultiClass',
    verbose=0,
    random_seed=42
)
best_model.fit(X_train, y_train)
y_pred = best_model.predict(X_test).reshape(-1)
report = classification_report(y_test, y_pred, target_names=['Normal', 'Slowloris', 'Quicly', 'LSQUIC'])
print("\nClassification Report:\n", report)

model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catboost_model")
os.makedirs(model_dir, exist_ok=True)
joblib.dump(best_model, os.path.join(model_dir, "catboost_best_model.pkl"))
joblib.dump(imputer, os.path.join(model_dir, "imputer.pkl"))

results = {
    "best_params": study.best_params,
    "classification_report": report
}
with open(os.path.join(model_dir, "catboost_results.json"), 'w') as f:
    json.dump(results, f, indent=4)

print(f"\nModel and results saved to {model_dir}")
del X, y, X_train, X_test, y_train, y_test, best_model, study
gc.collect()
