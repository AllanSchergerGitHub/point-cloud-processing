import numpy as np
import matplotlib.pyplot as plt

# Set random seed for reproducibility
np.random.seed(42)

# Parameters from the script
clusters = 4
cluster_size = 250
total_records = clusters * cluster_size

# Ranges from the script
balance_range = 100000 - 1000
rate_range = 12 - 4
term_range = 180 - 12

# Collect data
points = []

for _ in range(clusters):
    bal_center = np.random.uniform(1000, 100000)
    rate_center = np.random.uniform(4, 12)
    term_center = np.random.uniform(12, 180)

    for _ in range(cluster_size):
        balance = np.clip(np.random.normal(bal_center, balance_range / 20), 1000, 100000)
        rate = np.clip(np.random.normal(rate_center, rate_range / 10), 4, 12)
        term = np.clip(np.random.normal(term_center, term_range / 20), 12, 180)
        points.append((term, balance, rate))

points = np.array(points)

# Plot 3D scatter
fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(111, projection='3d')
ax.scatter(points[:, 0], points[:, 1], points[:, 2], alpha=0.6, s=10, c=points[:, 2], cmap='coolwarm')

ax.set_xlabel("Term (Months)")
ax.set_ylabel("Balance ($)")
ax.set_zlabel("Rate (%)")
ax.set_title("Loan Clusters: Term vs Balance vs Rate")

plt.tight_layout()
plt.show()
