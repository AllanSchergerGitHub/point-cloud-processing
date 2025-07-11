from __future__ import annotations

import argparse
import csv
import os
import random
import time
from typing import Iterable, List, Optional

import numpy as np
import open3d as o3d


def _add_axis_labels(vis: o3d.visualization.Visualizer, grid_size: float) -> None:
    """Display axis labels using the best method supported by Open3D."""
    labels = {
        "Term/Age": [grid_size * 0.25, grid_size * 0.05, 0.0],
        "Balance": [grid_size * 0.05, 0.0, grid_size * 0.25],
        "Rate": [0.0, grid_size * 0.25, grid_size * 0.05],
    }

    if hasattr(o3d.geometry.TriangleMesh, "create_text_3d"):
        for text, pos in labels.items():
            mesh = _text_mesh(text, pos, scale=0.08, color=(1.0, 1.0, 1.0))
            if mesh is not None:
                vis.add_geometry(mesh)
    elif hasattr(vis, "add_3d_label"):
        for text, pos in labels.items():
            vis.add_3d_label(pos, text)
    else:
        # No supported method for text rendering.
        pass


def add_face_titles(
    vis: o3d.visualization.Visualizer,
    grid_size: float,
    scale: float = 0.07,
    color=(1.0, 1.0, 1.0),
) -> None:
    """Place one title on each positive-axis face of the grid."""

    if not hasattr(o3d.geometry.TriangleMesh, "create_text_3d"):
        return  # Old Open3D build – silently skip

    eps = 0.03 * grid_size
    half = 0.5 * grid_size

    definitions = [
        ("Term/Age", [half, -eps, 0.0]),
        ("Balance", [-eps, half, 0.0]),
        ("Rate", [-eps, -eps, half]),
    ]

    for text, pos in definitions:
        mesh = _text_mesh(text, pos, scale=scale, color=color)
        vis.add_geometry(mesh)

def _text_mesh(
    text: str,
    position: Iterable[float],
    scale: float = 0.05,
    color: Optional[Iterable[float]] = None,
) -> Optional[o3d.geometry.TriangleMesh]:
    """Return an extruded 3D text mesh translated to ``position``.

    If the current Open3D installation does not provide the
    ``TriangleMesh.create_text_3d`` method, ``None`` is returned and the
    caller should fall back to 2D labels if available.
    """

    if not hasattr(o3d.geometry.TriangleMesh, "create_text_3d"):
        # Older Open3D versions (<0.20) do not support 3D text meshes.
        return None

    mesh = o3d.geometry.TriangleMesh.create_text_3d(
        text,
        depth=0.01,
        font_size=20,
    )
    if color is not None:
        mesh.paint_uniform_color(list(color))
    mesh.scale(scale, center=(0.0, 0.0, 0.0))
    mesh.translate(list(position))
    return mesh

# Default number of records used when generating sample data.
DEFAULT_NUM_RECORDS = 500

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
    size: float = 1.0,
    divisions: int = 10,
    plane: str = "xy",
    positive_only: bool = False,
) -> o3d.geometry.LineSet:
    """Return a faint grid in one of the principal planes.

    Parameters
    ----------
    size : float
        Length of a side of the grid.
    divisions : int
        Number of grid segments.
    plane : str
        Plane in which to build the grid ("xy", "xz", or "yz").
    positive_only : bool
        If true, the grid originates at 0 instead of being centered."""
    plane = plane.lower()
    if plane not in ("xy", "xz", "yz"):
        raise ValueError("plane must be 'xy', 'xz', or 'yz'")
    points = []
    lines = []
    step = size / divisions
    origin = 0.0 if positive_only else -size / 2

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


def _create_background_wall(
    width: float,
    height: float,
    depth: float,
    offset: List[float],
    axis: str = "xy",
    color=(0.1, 0.1, 0.1),
) -> o3d.geometry.TriangleMesh:
    """Return a thin colored plane placed behind a grid."""

    mesh = o3d.geometry.TriangleMesh.create_box(
        width=width, height=height, depth=depth
    )
    mesh.paint_uniform_color(list(color))
    mesh.translate(offset)
    return mesh


def _create_wall_text(
    text: str,
    position: List[float],
    plane: str = "xy",
    scale: float = 0.05,
    color=(1.0, 1.0, 1.0),
) -> Optional[o3d.geometry.TriangleMesh]:
    """Return a text mesh oriented on the given plane."""

    mesh = _text_mesh(text, [0.0, 0.0, 0.0], scale=scale, color=color)
    if mesh is None:
        return None

    plane = plane.lower()
    if plane == "xz":
        rot = o3d.geometry.get_rotation_matrix_from_xyz((np.pi / 2, 0.0, 0.0))
        mesh.rotate(rot, center=(0.0, 0.0, 0.0))
    elif plane == "yz":
        rot = o3d.geometry.get_rotation_matrix_from_xyz((0.0, np.pi / 2, 0.0))
        mesh.rotate(rot, center=(0.0, 0.0, 0.0))
    elif plane != "xy":
        raise ValueError("plane must be 'xy', 'xz', or 'yz'")

    mesh.translate(list(position))
    return mesh



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
    grid_size = 1.1

    grid_xy = _create_grid(size=grid_size, divisions=10, plane="xy", positive_only=True)
    grid_xz = _create_grid(size=grid_size, divisions=10, plane="xz", positive_only=True)
    grid_yz = _create_grid(size=grid_size, divisions=10, plane="yz", positive_only=True)
    wall_xy = _create_background_wall(
        grid_size,
        grid_size,
        0.001,
        [0.0, 0.0, -0.001],
        "xy",
    )
    wall_xz = _create_background_wall(
        grid_size,
        0.001,
        grid_size,
        [0.0, -0.001, 0.0],
        "xz",
    )
    wall_yz = _create_background_wall(
        0.001,
        grid_size,
        grid_size,
        [-0.001, 0.0, 0.0],
        "yz",
    )

    wall_label = _create_wall_text(
        "Loan Portfolio",
        [0.05 * grid_size, 0.05 * grid_size, -0.0005],
        plane="xy",
        scale=0.08,
    )

    axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.2)
    vis.add_geometry(grid_xy)
    vis.add_geometry(grid_xz)
    vis.add_geometry(grid_yz)
    vis.add_geometry(wall_xy)
    vis.add_geometry(wall_xz)
    vis.add_geometry(wall_yz)

    if wall_label is not None:
        vis.add_geometry(wall_label)

    vis.add_geometry(axis)
    add_face_titles(vis, grid_size)

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
            grid_xy = _create_grid(size=grid_size, divisions=10, plane="xy", positive_only=True)
            grid_xz = _create_grid(size=grid_size, divisions=10, plane="xz", positive_only=True)
            grid_yz = _create_grid(size=grid_size, divisions=10, plane="yz", positive_only=True)
            wall_xy = _create_background_wall(
                grid_size,
                grid_size,
                0.001,
                [0.0, 0.0, -0.001],
                "xy",
            )
            wall_xz = _create_background_wall(
                grid_size,
                0.001,
                grid_size,
                [0.0, -0.001, 0.0],
                "xz",
            )
            wall_yz = _create_background_wall(
                0.001,
                grid_size,
                grid_size,
                [-0.001, 0.0, 0.0],
                "yz",
            )

            wall_label = _create_wall_text(
                "Loan Portfolio",
                [0.05 * grid_size, 0.05 * grid_size, -0.0005],
                plane="xy",
                scale=0.08,
            )

            axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.2)
            vis.add_geometry(grid_xy)
            vis.add_geometry(grid_xz)
            vis.add_geometry(grid_yz)
            vis.add_geometry(wall_xy)
            vis.add_geometry(wall_xz)
            vis.add_geometry(wall_yz)

            if wall_label is not None:
                vis.add_geometry(wall_label)

            vis.add_geometry(axis)
            add_face_titles(vis, grid_size)

            vis.get_view_control().convert_from_pinhole_camera_parameters(camera)
    except KeyboardInterrupt:
        pass
    finally:
        vis.destroy_window()


if __name__ == "__main__":
    main()
