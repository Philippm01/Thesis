import os
import glob
import joblib
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

parser = argparse.ArgumentParser(description='Evaluate an XGBoost model and generate a confusion matrix.')
parser.add_argument('model_path', type=str, help='Absolute path to the saved XGBoost model file (xgboost_best_model.pkl).')
parser.add_argument('--caption', type=str, default='Confusion Matrix', help='Custom description for the confusion matrix caption.')
args = parser.parse_args()

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

    dfs = load_csv_files(csv_files, scenario_config[scenario]["label"])
    dataframes.extend(dfs)

data = pd.concat(dataframes, ignore_index=True)

X = data.drop(columns=['label'])
y = data['label']
imputer = joblib.load(os.path.join(os.path.dirname(args.model_path), "imputer.pkl"))
X_imputed = imputer.transform(X)

_, X_test, _, y_test = train_test_split(
    X_imputed, y, test_size=0.2, random_state=42, stratify=y
)

model = joblib.load(args.model_path)
y_pred = model.predict(X_test)

cm = confusion_matrix(y_test, y_pred)
display_labels = ['Normal', 'Slowloris', 'Quicly', 'LSQUIC']

plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=display_labels, yticklabels=display_labels)
plt.title(args.caption)  # Use the custom caption argument
plt.xlabel('Predicted Labels')
plt.ylabel('True Labels')
plt.tight_layout()
output_dir = os.path.dirname(args.model_path)
plt.savefig(os.path.join(output_dir, "confusion_matrix.png"))
plt.show()

print(f"Confusion matrix saved to {output_dir}/confusion_matrix.png")
