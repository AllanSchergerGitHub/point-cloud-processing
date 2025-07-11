import argparse
import csv
import os
import random
import time
from typing import Iterable, List

import numpy as np
import open3d as o3d

# Default number of records used when generating sample data.
DEFAULT_NUM_RECORDS = 2500

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


def _generate_clustered_loans(
    num_records: int = DEFAULT_NUM_RECORDS, clusters: int = 4
) -> List[dict]:
    """Return a list of clustered loan records."""
    records: List[dict] = []
    base_balance_range = 100_000 - 1_000
    base_rate_range = 12 - 4
    base_term_range = 180 - 12
    cluster_size = num_records // clusters

    for idx in range(clusters):
        size = cluster_size
        if idx == clusters - 1:
            size = num_records - len(records)
        bal_center = random.uniform(1_000, 100_000)
        rate_center = random.uniform(4, 12)
        term_center = random.uniform(12, 180)
        for _ in range(size):
            balance = random.gauss(bal_center, base_balance_range / 20)
            rate = random.gauss(rate_center, base_rate_range / 10)
            term = random.gauss(term_center, base_term_range / 20)
            balance = min(max(balance, 1_000), 100_000)
            rate = min(max(rate, 4), 12)
            term = int(min(max(term, 12), 180))
            flag = "added" if random.random() < 0.5 else "removed"
            records.append(
                {
                    "loanbalance": f"{balance:.2f}",
                    "loanrate": f"{rate:.2f}",
                    "loanaddedOrRemovedFlag": flag,
                    "loantermOrAgeInMonths": str(term),
                    "cluster": str(idx + 1),
                }
            )
    random.shuffle(records)
    return records


def generate_sample_csv(
    path: str, num_records: int = DEFAULT_NUM_RECORDS, clusters: int = 4
) -> None:
    """Write clustered sample loan data to ``path``."""
    fieldnames = [
        "loanbalance",
        "loanrate",
        "loanaddedOrRemovedFlag",
        "loantermOrAgeInMonths",
        "cluster",
    ]
    data = _generate_clustered_loans(num_records=num_records, clusters=clusters)
    with open(path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


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
        radius = 0.002 + 0.002 * normalized
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
        if idx < 99 and hasattr(vis, "add_3d_label"):
            vis.add_3d_label(sphere.get_center(), str(idx + 1))


def _create_grid(
    size: float = 1.0, divisions: int = 10, plane: str = "xy"
) -> o3d.geometry.LineSet:
    """Return a faint grid in one of the principal planes."""
    plane = plane.lower()
    if plane not in ("xy", "xz", "yz"):
        raise ValueError("plane must be 'xy', 'xz', or 'yz'")
    points = []
    lines = []
    step = size / divisions
    origin = -size / 2

    # Lines parallel to the first axis in the plane
    for i in range(divisions + 1):
        if plane == "xy":
            start = [origin, origin + i * step, 0.0]
            end = [origin + size, origin + i * step, 0.0]
        elif plane == "xz":
            start = [origin, 0.0, origin + i * step]
            end = [origin + size, 0.0, origin + i * step]
        else:  # yz
            start = [0.0, origin, origin + i * step]
            end = [0.0, origin + size, origin + i * step]
        points.extend([start, end])
        lines.append([len(points) - 2, len(points) - 1])

    # Lines parallel to the second axis in the plane
    for i in range(divisions + 1):
        if plane == "xy":
            start = [origin + i * step, origin, 0.0]
            end = [origin + i * step, origin + size, 0.0]
        elif plane == "xz":
            start = [origin + i * step, 0.0, origin]
            end = [origin + i * step, 0.0, origin + size]
        else:  # yz
            start = [0.0, origin + i * step, origin]
            end = [0.0, origin + i * step, origin + size]
        points.extend([start, end])
        lines.append([len(points) - 2, len(points) - 1])

    line_set = o3d.geometry.LineSet()
    line_set.points = o3d.utility.Vector3dVector(np.asarray(points))
    line_set.lines = o3d.utility.Vector2iVector(np.asarray(lines))
    colors = np.tile([0.7, 0.7, 0.7], (len(lines), 1))
    line_set.colors = o3d.utility.Vector3dVector(colors)
    return line_set


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualize loan portfolio data and monitor for updates"
    )
    parser.add_argument("csv_file", help="CSV file containing loan data")
    args = parser.parse_args()

    csv_path = args.csv_file
    answer = input(
        f"Generate a new dataset with {DEFAULT_NUM_RECORDS:,d} sample records? [y/N]: "
    ).strip().lower()
    if answer == "y" or (answer == "" and not os.path.exists(csv_path)):
        generate_sample_csv(csv_path)
        print(f"Sample data written to {csv_path}")

    loans = load_loans(csv_path)
    spheres = loans_to_spheres(loans)

    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="Loan Portfolio")
    _add_spheres_to_visualizer(vis, spheres)

    grid_xy = _create_grid(size=1.0, divisions=20, plane="xy")
    grid_xz = _create_grid(size=1.0, divisions=20, plane="xz")
    grid_yz = _create_grid(size=1.0, divisions=20, plane="yz")
    axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.2)
    vis.add_geometry(grid_xy)
    vis.add_geometry(grid_xz)
    vis.add_geometry(grid_yz)
    vis.add_geometry(axis)
    if hasattr(vis, "add_3d_label"):
        vis.add_3d_label([0.25, 0, 0], "Term/Age")
        vis.add_3d_label([0, 0.25, 0], "Balance")
        vis.add_3d_label([0, 0, 0.25], "Rate")

    vis.poll_events()
    vis.update_renderer()

    try:
        last_mtime = os.path.getmtime(csv_path)
        prev_loans = loans
        check_interval = 5.0
        last_check = time.time()

        while True:
            vis.poll_events()
            vis.update_renderer()
            time.sleep(0.05)

            if time.time() - last_check < check_interval:
                continue
            last_check = time.time()

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

            camera = vis.get_view_control().convert_to_pinhole_camera_parameters()
            vis.clear_geometries()

            spheres = loans_to_spheres(new_loans)
            _add_spheres_to_visualizer(vis, spheres)
            grid_xy = _create_grid(size=1.0, divisions=20, plane="xy")
            grid_xz = _create_grid(size=1.0, divisions=20, plane="xz")
            grid_yz = _create_grid(size=1.0, divisions=20, plane="yz")
            axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.2)
            vis.add_geometry(grid_xy)
            vis.add_geometry(grid_xz)
            vis.add_geometry(grid_yz)
            vis.add_geometry(axis)
            if hasattr(vis, "add_3d_label"):
                vis.add_3d_label([0.25, 0, 0], "Term/Age")
                vis.add_3d_label([0, 0.25, 0], "Balance")
                vis.add_3d_label([0, 0, 0.25], "Rate")

            vis.get_view_control().convert_from_pinhole_camera_parameters(camera)
    except KeyboardInterrupt:
        pass
    finally:
        vis.destroy_window()


if __name__ == "__main__":
    main()
