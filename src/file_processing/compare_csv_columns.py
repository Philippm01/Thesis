import pandas as pd
import os

def load_csv_columns(file_path):
    try:
        df = pd.read_csv(file_path, nrows=0)  # Loading only the header row
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
    file_paths = [
        os.path.join(base_dir, 'normal/normal_time:180_it:1.csv'),
        os.path.join(base_dir, 'flooding/flood_con:20-50_time:180_it:1.csv'),
        os.path.join(base_dir, 'slowloris/slowloris_con:5-10_sleep:20-40_time:180_it:1.csv'),
        os.path.join(base_dir, 'quicly/quicly_time:180_it:1.csv'),
        os.path.join(base_dir, 'lsquic/lsquic_time:180_it:1.csv')
    ]

    compare_csv_columns(file_paths)

if __name__ == "__main__":
    main()
