import matplotlib.pyplot as plt
import numpy as np
import os

scenarios = ['Normal', 'Flood', 'Slowloris', 'Quicly', 'Lsquic']
ocsvm_percentages = [1, 10, 100, 31, 12]
isolation_forest_percentages = [1.2, 11, 73, 37, 6]  

bar_width = 0.35
y_pos = np.arange(len(scenarios))

plt.barh(y_pos - bar_width/2, ocsvm_percentages, bar_width, label='OCSVM', color='lightblue')
plt.barh(y_pos + bar_width/2, isolation_forest_percentages, bar_width, label='Isolation Forest', color='blue')

plt.yticks(y_pos, scenarios)
plt.xlabel('Attack Percentage of Predictions(%)')
plt.title('Predictions of OCSVM and Isolation Forest for different scenarios')
plt.xlim(0, 100)
plt.legend()
plt.tight_layout()

output_dir = "/home/philipp/Documents/Thesis/src/ocsvm"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "unsupervised_plot.png")
plt.savefig(output_path)
print(f"Plot saved to {output_path}")

plt.show()