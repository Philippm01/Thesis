import pandas as pd
import glob
import os
import json
import joblib
import optuna
import gc
import xgboost as xgb
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report
from sklearn.utils.class_weight import compute_class_weight

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

X_train, X_test, y_train, y_test = train_test_split(
    X_imputed, y, test_size=0.2, random_state=42, stratify=y
)

# Compute class weights
class_weights = compute_class_weight(class_weight='balanced', classes=np.unique(y_train), y=y_train)
class_weight_dict = dict(zip(np.unique(y_train), class_weights))
sample_weights = np.array([class_weight_dict[label] for label in y_train])

def objective(trial):
    params = {
        'objective': 'multi:softprob',
        'num_class': 4,
        'eval_metric': 'mlogloss',
        'verbosity': 0,
        'n_estimators': trial.suggest_int('n_estimators', 100, 500),
        'max_depth': trial.suggest_int('max_depth', 4, 16),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'gamma': trial.suggest_float('gamma', 0, 5),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'use_label_encoder': False,
        'random_state': 42,
        'n_jobs': -1
    }

    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train, sample_weight=sample_weights)
    y_pred = model.predict(X_test)
    return f1_score(y_test, y_pred, average='macro')

print("\nStarting Bayesian Search with Optuna...")
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=100, n_jobs=3)

print("\nBest parameters found:")
print(study.best_params)

print("\nEvaluating best model on test set...")
best_model = xgb.XGBClassifier(
    **study.best_params,
    objective='multi:softprob',
    num_class=4,
    use_label_encoder=False,
    eval_metric='mlogloss',
    random_state=42,
    n_jobs=-1
)
best_model.fit(X_train, y_train, sample_weight=sample_weights)

y_pred = best_model.predict(X_test)
report = classification_report(y_test, y_pred, target_names=['Normal', 'Slowloris', 'Quicly', 'LSQUIC'])
print("\nClassification Report:")
print(report)

model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "balanced_xgboost_model")
os.makedirs(model_dir, exist_ok=True)
joblib.dump(best_model, os.path.join(model_dir, "xgboost_balanced_model.pkl"))
joblib.dump(imputer, os.path.join(model_dir, "imputer.pkl"))

results = {
    "best_params": study.best_params,
    "classification_report": report
}
with open(os.path.join(model_dir, "xgboost_results.json"), 'w') as f:
    json.dump(results, f, indent=4)

print(f"\nModel and results saved to {model_dir}")

del X, y, X_train, X_test, y_train, y_test, best_model, study
gc.collect()