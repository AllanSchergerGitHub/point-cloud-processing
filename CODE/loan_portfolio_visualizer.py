import argparse
import csv
import os
import time
from typing import Iterable, List

import numpy as np
import open3d as o3d

"""Visualize loan portfolio data in 3D using Open3D.

This script requires the :mod:`open3d` package to be installed.
"""


def load_loans(csv_path):
    """Load loan data from a CSV file."""
    loans = []
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            loans.append(row)
    return loans


def _scale_features(array: np.ndarray) -> np.ndarray:
    """Scale the feature columns to the [0, 1] range."""
    mins = array.min(axis=0)
    maxs = array.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1.0
    return (array - mins) / ranges


def loans_to_spheres(loans: Iterable[dict]) -> List[o3d.geometry.TriangleMesh]:
    """Create scaled spheres for each loan entry."""
    points = []
    colors = []
    balances = []

    for row in loans:
        balance = float(row["loanbalance"])
        rate = float(row["loanrate"])
        term_or_age = float(row["loantermOrAgeInMonths"])
        flag = row["loanaddedOrRemovedFlag"].strip().lower()
        added = flag in ("added", "new", "1", "true", "yes")

        points.append([term_or_age, balance, rate])
        colors.append([0.0, 1.0, 0.0] if added else [1.0, 0.0, 0.0])
        balances.append(balance)

    points = _scale_features(np.array(points, dtype=float))
    balances = np.array(balances, dtype=float)
    min_balance = balances.min()
    max_balance = balances.max()
    balance_range = max_balance - min_balance or 1.0

    spheres: List[o3d.geometry.TriangleMesh] = []
    for idx, point in enumerate(points):
        normalized = (balances[idx] - min_balance) / balance_range
        radius = 0.05 + 0.1 * normalized
        mesh = o3d.geometry.TriangleMesh.create_sphere(radius=radius)
        mesh.translate(point)
        mesh.paint_uniform_color(colors[idx])
        spheres.append(mesh)

    return spheres


def _add_spheres_to_visualizer(
    vis: o3d.visualization.Visualizer, spheres: List[o3d.geometry.TriangleMesh]
) -> None:
    """Add spheres and numerical labels to the visualizer."""
    for idx, sphere in enumerate(spheres):
        vis.add_geometry(sphere)
        if idx < 99:
            vis.add_3d_label(sphere.get_center(), str(idx + 1))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualize loan portfolio data and monitor for updates"
    )
    parser.add_argument("csv_file", help="CSV file containing loan data")
    args = parser.parse_args()

    csv_path = args.csv_file
    loans = load_loans(csv_path)
    spheres = loans_to_spheres(loans)

    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="Loan Portfolio")
    _add_spheres_to_visualizer(vis, spheres)
    vis.poll_events()
    vis.update_renderer()

    try:
        last_mtime = os.path.getmtime(csv_path)
        prev_loans = loans
        while True:
            time.sleep(5)
            vis.poll_events()
            vis.update_renderer()

            try:
                mtime = os.path.getmtime(csv_path)
            except OSError:
                continue

            if mtime == last_mtime:
                continue
            last_mtime = mtime

            new_loans = load_loans(csv_path)
            if new_loans == prev_loans:
                continue
            prev_loans = new_loans

            vis.clear_geometries()
            spheres = loans_to_spheres(new_loans)
            _add_spheres_to_visualizer(vis, spheres)
    except KeyboardInterrupt:
        pass
    finally:
        vis.destroy_window()


if __name__ == "__main__":
    main()
