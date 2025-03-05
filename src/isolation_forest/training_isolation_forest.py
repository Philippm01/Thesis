import pandas as pd
import glob
from netml.ndm.model import MODEL
from netml.ndm.isolation_forest import IsolationForest
from netml.utils.tool import dump_data, load_data
from sklearn.model_selection import train_test_split

RANDOM_STATE = 42

# Path to normal traffic dataset (all CSVs)
dataset_path = "/home/philipp/Documents/Thesis/session_Datasets/normal/*.csv"

# Load all normal CSV files
csv_files = glob.glob(dataset_path)

# Use only the first 80 files for training
training_files = csv_files[:80]
dataframes = []

# Load all feature names
all_features = sorted(set(pd.read_csv(training_files[0]).columns))

for file in training_files:
    df = pd.read_csv(file)

    # Ensure all features exist, fill missing ones with NaN
    for feature in all_features:
        if feature not in df.columns:
            df[feature] = float('nan')
    
    # Align column order
    df = df[all_features]
 
    dataframes.append(df)

# Combine all normal NetML feature data into one dataset
df_normal = pd.concat(dataframes, ignore_index=True)

# Convert DataFrame to NumPy array
features = df_normal.values
labels = [0] * len(features)  # Assume all data is normal

# Split train and test sets
features_train, features_test, labels_train, labels_test = train_test_split(
    features, labels, test_size=0.33, random_state=RANDOM_STATE
)

# Create and train detection model
iso_forest = IsolationForest(n_estimators=100, contamination=0.05, random_state=RANDOM_STATE)
iso_forest.name = 'IsolationForest'
ndm = MODEL(iso_forest, score_metric='auc', verbose=10, random_state=RANDOM_STATE)
ndm.train(features_train)

# Evaluate the trained model
ndm.test(features_test, labels_test)

# Dump model and training history
dump_data((iso_forest, ndm.history), out_file='/home/philipp/Documents/Thesis/src/ocsvm/IsolationForest-results.dat')

# Stats
print(ndm.train.tot_time, ndm.test.tot_time, ndm.score)
print("✅ Isolation Forest model trained and saved with NetML")
