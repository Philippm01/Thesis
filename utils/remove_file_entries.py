import json

input_path = "/home/philipp/Documents/Thesis/src/ocsvm/model_2_test_results.json"
output_path = "/home/philipp/Documents/Thesis/src/ocsvm/ocvsm_gridsearch_cleaned.json"

def remove_file_entries(input_file, output_file):
    with open(input_file, "r") as f:
        data = json.load(f)

    for model in data.get("models", []):
        for scenario in model.get("scenarios", []):
            if "files" in scenario:
                print(f"Removing 'files' from scenario: {scenario['scenario']}")  # Debugging
                del scenario["files"]

    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)

remove_file_entries(input_path, output_path)