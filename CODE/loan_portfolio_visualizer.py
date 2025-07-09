import argparse
import csv
import numpy as np
import open3d as o3d


def load_loans(csv_path):
    """Load loan data from a CSV file."""
    loans = []
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            loans.append(row)
    return loans


def loans_to_point_cloud(loans):
    """Convert loan records to an Open3D point cloud."""
    points = []
    colors = []
    for row in loans:
        balance = float(row["loanbalance"])
        rate = float(row["loanrate"])
        term_or_age = float(row["loantermOrAgeInMonths"])
        flag = row["loanaddedOrRemovedFlag"].strip().lower()
        added = flag in ("added", "new", "1", "true", "yes")

        points.append([term_or_age, balance, rate])
        colors.append([0.0, 1.0, 0.0] if added else [1.0, 0.0, 0.0])

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(np.array(points, dtype=float))
    cloud.colors = o3d.utility.Vector3dVector(np.array(colors, dtype=float))
    return cloud


def main():
    parser = argparse.ArgumentParser(description="Visualize loan portfolio data")
    parser.add_argument("csv_file", help="CSV file containing loan data")
    args = parser.parse_args()

    loans = load_loans(args.csv_file)
    cloud = loans_to_point_cloud(loans)
    o3d.visualization.draw_geometries([cloud])


if __name__ == "__main__":
    main()
