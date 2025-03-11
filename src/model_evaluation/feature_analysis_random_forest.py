import pandas as pd
import numpy as np
import joblib
import shap
import matplotlib.pyplot as plt
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
import argparse
import os

def analyze_predictions(model, data, feature_names, model_name, csv_name):
    predictions = model.predict(data)
    binary_predictions = np.where(predictions == 1, 1, 0)
    
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(data, binary_predictions)
    
    feature_importance = rf_model.feature_importances_
    feature_importance_dict = dict(zip(feature_names, feature_importance))
    sorted_features = dict(sorted(feature_importance_dict.items(), key=lambda x: abs(x[1]), reverse=True))
    
    plt.figure(figsize=(10, 6))
    features = list(sorted_features.keys())[:20]
    importances = [sorted_features[f] for f in features]
    
    plt.barh(range(len(features)), importances)
    plt.yticks(range(len(features)), features)
    plt.xlabel('Feature Importance')
    plt.title('Top 20 Most Important Features')
    plt.tight_layout()
    plt.savefig(f'feature_importance_{model_name}_{os.path.splitext(csv_name)[0]}.png')
    plt.close()
    
    return sorted_features

def main():
    parser = argparse.ArgumentParser(description='Analyze feature importance using Random Forest')
    parser.add_argument('--model-path', type=str, required=True,
                       help='Path to model file relative to source directory')
    parser.add_argument('--csv-file', type=str, required=True,
                       help='Path to CSV file relative base directory')
    args = parser.parse_args()

    base_dir = "/home/philipp/Documents/Thesis"
    model_full_path = os.path.join(base_dir+"/src", args.model_path)
    csv_full_path = os.path.join(base_dir, args.csv_file)
    
    model_name = os.path.splitext(os.path.basename(args.model_path))[0]
    csv_name = os.path.basename(args.csv_file)
    
    try:
        model = joblib.load(model_full_path)
        print(f"Model loaded successfully from {model_full_path}")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    try:
        df = pd.read_csv(csv_full_path)
        feature_names = df.columns.tolist()
        
        imputer = SimpleImputer(strategy='mean')
        X = imputer.fit_transform(df)
        
        predictions = model.predict(X)
        normal_count = sum(predictions == 1)
        attack_count = sum(predictions == -1)
        total = len(predictions)
        
        print("\nPrediction Summary:")
        print(f"Normal streams: {normal_count} ({normal_count/total*100:.2f}%)")
        print(f"Attack streams: {attack_count} ({attack_count/total*100:.2f}%)")
        
        print("\nAnalyzing feature importance...")
        feature_importance = analyze_predictions(model, X, feature_names, model_name, csv_name)
        
        print("\nTop 10 Most Important Features:")
        for i, (feature, importance) in enumerate(list(feature_importance.items())[:10], 1):
            print(f"{i}. {feature}: {abs(importance):.4f}")
        
        output_file = f'feature_importance_{model_name}_{os.path.splitext(csv_name)[0]}.txt'
        output_dir = os.path.dirname(model_full_path)
        with open(os.path.join(output_dir, output_file), 'w') as f:
            f.write("Feature Importance Analysis\n")
            f.write("=========================\n\n")
            f.write(f"Analyzed file: {args.csv_file}\n")
            f.write(f"Total streams: {total}\n")
            f.write(f"Normal streams: {normal_count} ({normal_count/total*100:.2f}%)\n")
            f.write(f"Attack streams: {attack_count} ({attack_count/total*100:.2f}%)\n\n")
            f.write("Feature Importance Ranking:\n")
            for feature, importance in feature_importance.items():
                f.write(f"{feature}: {abs(importance):.4f}\n")
        
        print(f"\nDetailed results saved to {os.path.join(output_dir, output_file)}")
        print(f"Feature importance plot saved as feature_importance_{model_name}_{os.path.splitext(csv_name)[0]}.png")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return

if __name__ == "__main__":
    main()
