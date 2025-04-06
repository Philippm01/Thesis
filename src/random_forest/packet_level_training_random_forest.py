import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from collections import Counter


csv_path = "all_iterations_quic_packets.csv"
df = pd.read_csv(csv_path)

X = df.drop(columns=["Attack Type"])
y = df["Attack Type"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

print("Label distribution in full set:", Counter(y))
print("Label distribution in train:", Counter(y_train))
print("Label distribution in test:", Counter(y_test))

clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

y_pred = clf.predict(X_test)
print("\nClassification Report:")
print(classification_report(y_test, y_pred, digits=4))
