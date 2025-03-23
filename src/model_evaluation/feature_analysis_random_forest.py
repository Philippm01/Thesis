import os
import glob
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.impute import SimpleImputer
from sklearn.tree import DecisionTreeClassifier

def load_data_and_label(base_dir, scenario_pair):
    """
    Reads CSVs from 'normal' and one attack scenario folder.
    Assigns labels: normal -> 0, attack -> 1
    """
    folder_label_map = {
        "normal": 0,
        scenario_pair: 1
    }
    
    all_dfs = []
    for folder_name, label_val in folder_label_map.items():
        folder_path = os.path.join(base_dir, folder_name)
        csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
        
        if not csv_files:
            print(f"No CSV files found in {folder_path}")
            continue
        
        for file_path in csv_files:
            df = pd.read_csv(file_path)
            df["Label"] = label_val
            all_dfs.append(df)
    
    if not all_dfs:
        raise ValueError(f"No data found for normal and {scenario_pair}")
    
    combined_df = pd.concat(all_dfs, ignore_index=True)
    return combined_df

def plot_feature_importance(feature_names, importances, output_prefix="feature_importance"):
    feat_imp_pairs = list(zip(feature_names, importances))
    feat_imp_pairs.sort(key=lambda x: abs(x[1]), reverse=True)
    print("\nFeature Importances:")
    for i, (fname, imp) in enumerate(feat_imp_pairs, start=1):
        print(f"{i}. {fname}: {imp:.4f}")
    
    features = [x[0] for x in feat_imp_pairs]
    importance = [x[1] for x in feat_imp_pairs]
    
    plt.figure(figsize=(10, 6))
    plt.barh(range(len(features)), importance, color='skyblue')
    plt.yticks(range(len(features)), features)
    plt.gca().invert_yaxis()  
    plt.xlabel("Feature Importance")
    plt.title("Decision Tree Feature Importances")
    plt.tight_layout()
    
    output_filename = f"{output_prefix}.png"
    plt.savefig(output_filename, dpi=150)
    plt.close()
    print(f"Feature importance plot saved as '{output_filename}'")

def analyze_scenario(base_dir, scenario):
    print(f"\nAnalyzing {scenario} vs normal traffic:")
    df = load_data_and_label(base_dir, scenario)
    target_col = "Label"
    feature_cols = [c for c in df.columns if c != target_col]
    
    X_df = df[feature_cols]
    y = df[target_col].values
    
    imputer = SimpleImputer(strategy='mean')
    X = imputer.fit_transform(X_df)
    feature_names = X_df.columns.tolist()
    
    clf = DecisionTreeClassifier(random_state=42)
    clf.fit(X, y)
    
    importances = clf.feature_importances_
    plot_feature_importance(feature_names, importances, f"decision_tree_importance_{scenario}")

def main():
    base_dir = "/home/philipp/Documents/Thesis/session_Datasets"
    
    # Analyze each attack scenario separately
    analyze_scenario(base_dir, "lsquic")
    analyze_scenario(base_dir, "quicly")

if __name__ == "__main__":
    main()
