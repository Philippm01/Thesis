import pandas as pd
import os

def load_csv_columns(file_path):
    try:
        df = pd.read_csv(file_path, nrows=0)  
        return df.columns.tolist()
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def compare_csv_columns(file_paths):
    reference_columns = None
    for file_path in file_paths:
        columns = load_csv_columns(file_path)
        if columns is None:
            continue

        if reference_columns is None:
            reference_columns = columns
            print(f"Reference columns set from {file_path}")
        else:
            if columns != reference_columns:
                print(f"Column mismatch in {file_path}")
                print(f"Expected: {reference_columns}")
                print(f"Found: {columns}")
            else:
                print(f"Columns match for {file_path}")

def main():
    base_dir = '/home/philipp/Documents/Thesis/session_Datasets'
    file_paths = []
    for subdir, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.csv'):
                file_path = os.path.join(subdir, file)
                file_paths.append(file_path)

    compare_csv_columns(file_paths)

if __name__ == "__main__":
    main()
