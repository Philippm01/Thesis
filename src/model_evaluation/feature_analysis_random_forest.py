#!/usr/bin/env python3

import os
import glob
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.impute import SimpleImputer
from sklearn.tree import DecisionTreeClassifier

def load_data_and_label(base_dir="session_dataset"):
    folder_label_map = {
        "normal": 0,
        "quicly": 1,
        "lsquic": 2
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
        raise ValueError(f"No data found in subfolders of {base_dir}")
    
    combined_df = pd.concat(all_dfs, ignore_index=True)
    return combined_df

def plot_feature_importance(feature_names, importances, output_prefix="feature_importance"):

    feat_imp_pairs = list(zip(feature_names, importances))
    feat_imp_pairs.sort(key=lambda x: abs(x[1]), reverse=True)

    print("\nTop 10 Most Important Features:")
    for i, (fname, imp) in enumerate(feat_imp_pairs[:10], start=1):
        print(f"{i}. {fname}: {imp:.4f}")
    top_20 = feat_imp_pairs[:20]
    features_20 = [x[0] for x in top_20]
    importance_20 = [x[1] for x in top_20]
    
    plt.figure(figsize=(8, 6))
    plt.barh(range(len(features_20)), importance_20, color='skyblue')
    plt.yticks(range(len(features_20)), features_20)
    plt.gca().invert_yaxis()  
    plt.xlabel("Feature Importance")
    plt.title("Top 20 Decision Tree Feature Importances")
    plt.tight_layout()
    
    output_filename = f"{output_prefix}.png"
    plt.savefig(output_filename, dpi=150)
    plt.close()
    print(f"Feature importance plot saved as '{output_filename}'")

def main():
    df = load_data_and_label(base_dir="/home/philipp/Documents/Thesis/session_Datasets")
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
    
    plot_feature_importance(feature_names, importances, output_prefix="decision_tree_importance")

if __name__ == "__main__":
    main()
