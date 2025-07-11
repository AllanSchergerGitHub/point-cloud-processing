"""Plot loan portfolio metrics from a CSV file using Matplotlib."""

import argparse
import csv
from typing import List

import matplotlib.pyplot as plt
import numpy as np


def load_loans(csv_path: str) -> List[dict]:
    """Return a list of loan records from ``csv_path``."""

    loans: List[dict] = []
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            loans.append(row)
    return loans


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot loan data from CSV")
    parser.add_argument("csv_file", help="CSV file containing loan data")
    args = parser.parse_args()

    loans = load_loans(args.csv_file)

    points = np.array(
        [
            [
                float(row["loantermOrAgeInMonths"]),
                float(row["loanbalance"]),
                float(row["loanrate"]),
            ]
            for row in loans
        ],
        dtype=float,
    )
    clusters = np.array([int(row.get("cluster", 0)) for row in loans], dtype=int)

    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    sc = ax.scatter(
        points[:, 0],
        points[:, 1],
        points[:, 2],
        c=clusters,
        cmap="tab10",
        alpha=0.6,
        s=10,
    )
    legend1 = ax.legend(*sc.legend_elements(), title="Cluster")
    ax.add_artist(legend1)

    ax.set_xlabel("Term (Months)")
    ax.set_ylabel("Balance ($)")
    ax.set_zlabel("Rate (%)")
    ax.set_title("Loan Clusters: Term vs Balance vs Rate")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
