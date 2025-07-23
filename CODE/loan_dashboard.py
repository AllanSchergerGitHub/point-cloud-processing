#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from typing import Iterable, List

import numpy as np
import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering


def load_loans(csv_path: str) -> List[dict]:
    """Return a list of loan records from ``csv_path``."""
    loans: List[dict] = []
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            loans.append(row)
    return loans


def loan_stats(loans: Iterable[dict]) -> dict:
    """Return basic statistics for the loan dataset."""
    balances = np.array([float(r["loanbalance"]) for r in loans], dtype=float)
    rates = np.array([float(r["loanrate"]) for r in loans], dtype=float)
    terms = np.array([float(r["loantermOrAgeInMonths"]) for r in loans], dtype=float)
    return {
        "count": len(loans),
        "avg_balance": float(balances.mean()) if len(balances) else 0.0,
        "avg_rate": float(rates.mean()) if len(rates) else 0.0,
        "avg_term": float(terms.mean()) if len(terms) else 0.0,
    }


def loans_to_point_cloud(
    loans: Iterable[dict], x: str, y: str, z: str
) -> o3d.geometry.PointCloud:
    """Return a :class:`~open3d.geometry.PointCloud` for the given axis mapping."""
    points = []
    colors = []
    for row in loans:
        points.append([
            float(row[x]),
            float(row[y]),
            float(row[z]),
        ])
        flag = row.get("loanaddedOrRemovedFlag", "").strip().lower()
        added = flag in ("added", "new", "1", "true", "yes")
        colors.append([0.0, 1.0, 0.0] if added else [1.0, 0.0, 0.0])

    pc = o3d.geometry.PointCloud()
    pc.points = o3d.utility.Vector3dVector(np.asarray(points, dtype=float))
    pc.colors = o3d.utility.Vector3dVector(np.asarray(colors, dtype=float))
    return pc


class Dashboard:
    def __init__(self, csv_path: str) -> None:
        self.csv_path = csv_path
        self.loans = load_loans(csv_path)
        self.x_col = "loantermOrAgeInMonths"
        self.y_col = "loanbalance"
        self.z_col = "loanrate"

        gui.Application.instance.initialize()
        self.window = gui.Application.instance.create_window(
            "Loan Dashboard", 1024, 768
        )
        self.scene = gui.SceneWidget()
        self.scene.scene = rendering.Open3DScene(self.window.renderer)
        self.window.add_child(self.scene)

        self.panel = gui.Vert(0, gui.Margins(10, 10, 10, 10))
        self.window.add_child(self.panel)

        self.stats_label = gui.Label("")
        self.panel.add_child(self.stats_label)

        self.panel.add_child(gui.Label("X axis:"))
        self.x_combo = gui.Combobox()
        for key in self._numeric_keys():
            self.x_combo.add_item(key)
        self.x_combo.set_on_selection_changed(self._update_axes)
        self.panel.add_child(self.x_combo)

        self.panel.add_child(gui.Label("Y axis:"))
        self.y_combo = gui.Combobox()
        for key in self._numeric_keys():
            self.y_combo.add_item(key)
        self.y_combo.set_on_selection_changed(self._update_axes)
        self.panel.add_child(self.y_combo)

        self.panel.add_child(gui.Label("Z axis:"))
        self.z_combo = gui.Combobox()
        for key in self._numeric_keys():
            self.z_combo.add_item(key)
        self.z_combo.set_on_selection_changed(self._update_axes)
        self.panel.add_child(self.z_combo)

        self.panel.add_child(gui.Label("Rotation:"))
        self.pitch = self._slider("Pitch", self._update_rotation)
        self.yaw = self._slider("Yaw", self._update_rotation)
        self.roll = self._slider("Roll", self._update_rotation)

        self.window.set_on_layout(self._on_layout)
        self._update_stats()
        self._update_scene()
        gui.Application.instance.run()

    def _numeric_keys(self) -> List[str]:
        sample = self.loans[0]
        return [k for k, v in sample.items() if self._is_float(v)]

    @staticmethod
    def _is_float(value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _slider(self, name: str, callback) -> gui.Slider:
        slider = gui.Slider(gui.Slider.DOUBLE)
        slider.set_limits(-180.0, 180.0)
        slider.set_on_value_changed(callback)
        self.panel.add_child(gui.Label(name))
        self.panel.add_child(slider)
        return slider

    def _on_layout(self, ctx):
        r = self.window.content_rect
        panel_width = 240
        self.scene.frame = gui.Rect(r.x, r.y, r.width - panel_width, r.height)
        self.panel.frame = gui.Rect(
            r.get_right() - panel_width, r.y, panel_width, r.height
        )

    def _update_stats(self) -> None:
        stats = loan_stats(self.loans)
        self.stats_label.text = (
            f"Records: {stats['count']}\n"
            f"Avg Balance: {stats['avg_balance']:.2f}\n"
            f"Avg Rate: {stats['avg_rate']:.2f}%\n"
            f"Avg Term: {stats['avg_term']:.1f} months"
        )

    def _update_axes(self, text: str, index: int) -> None:  # noqa: D401
        del text, index
        self.x_col = self.x_combo.selected_text
        self.y_col = self.y_combo.selected_text
        self.z_col = self.z_combo.selected_text
        self._update_scene()

    def _update_scene(self) -> None:
        pc = loans_to_point_cloud(self.loans, self.x_col, self.y_col, self.z_col)
        mat = rendering.MaterialRecord()
        mat.shader = "defaultUnlit"

        self.scene.scene.clear_geometry()
        self.scene.scene.add_geometry("loans", pc, mat)
        bounds = pc.get_axis_aligned_bounding_box()
        self.center = bounds.get_center()
        self.radius = max(bounds.extent) * 1.5
        self.scene.setup_camera(60.0, bounds, self.center)
        self._update_rotation()

    def _update_rotation(self, value: float = 0.0) -> None:  # noqa: D401
        del value
        pitch = np.radians(self.pitch.double_value)
        yaw = np.radians(self.yaw.double_value)
        roll = np.radians(self.roll.double_value)
        R = o3d.geometry.get_rotation_matrix_from_xyz((pitch, yaw, roll))
        direction = R @ np.array([0.0, 0.0, -self.radius])
        up = R @ np.array([0.0, 1.0, 0.0])
        eye = self.center - direction
        self.scene.scene.camera.look_at(self.center, eye, up)


def main() -> None:
    parser = argparse.ArgumentParser(description="Loan dashboard")
    parser.add_argument("csv_file", help="CSV file with loan data")
    args = parser.parse_args()
    Dashboard(args.csv_file)


if __name__ == "__main__":
    main()
