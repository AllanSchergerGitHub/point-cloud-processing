#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import Iterable, List

import numpy as np
import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering

from loan_portfolio_visualizer import (
    load_loans,
    loans_to_spheres,
    _create_background_wall,
    _create_grid,
    _create_wall_text,
    add_face_titles,
)


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
        self.x_combo.selected_text = self.x_col
        self.x_combo.set_on_selection_changed(self._update_axes)
        self.panel.add_child(self.x_combo)

        self.panel.add_child(gui.Label("Y axis:"))
        self.y_combo = gui.Combobox()
        for key in self._numeric_keys():
            self.y_combo.add_item(key)
        self.y_combo.selected_text = self.y_col
        self.y_combo.set_on_selection_changed(self._update_axes)
        self.panel.add_child(self.y_combo)

        self.panel.add_child(gui.Label("Z axis:"))
        self.z_combo = gui.Combobox()
        for key in self._numeric_keys():
            self.z_combo.add_item(key)
        self.z_combo.selected_text = self.z_col
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
        spheres = loans_to_spheres(
            self.loans, self.x_col, self.y_col, self.z_col
        )
        mesh_mat = rendering.MaterialRecord()
        mesh_mat.shader = "defaultLit"

        line_mat = rendering.MaterialRecord()
        line_mat.shader = "unlitLine"

        self.scene.scene.clear_geometry()

        for idx, sphere in enumerate(spheres):
            self.scene.scene.add_geometry(f"sphere_{idx}", sphere, mesh_mat)

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

        self.scene.scene.add_geometry("grid_xy", grid_xy, line_mat)
        self.scene.scene.add_geometry("grid_xz", grid_xz, line_mat)
        self.scene.scene.add_geometry("grid_yz", grid_yz, line_mat)
        self.scene.scene.add_geometry("wall_xy", wall_xy, mesh_mat)
        self.scene.scene.add_geometry("wall_xz", wall_xz, mesh_mat)
        self.scene.scene.add_geometry("wall_yz", wall_yz, mesh_mat)

        label = _create_wall_text(
            "Loan Portfolio", [0.05 * grid_size, 0.05 * grid_size, -0.0005], plane="xy", scale=0.08
        )
        if label is not None:
            self.scene.scene.add_geometry("label", label, mesh_mat)

        add_face_titles(self.scene.scene, grid_size)

        all_geometry = spheres + [grid_xy, grid_xz, grid_yz, wall_xy, wall_xz, wall_yz]
        if label is not None:
            all_geometry.append(label)
        bbox = all_geometry[0].get_axis_aligned_bounding_box()
        for g in all_geometry[1:]:
            bbox += g.get_axis_aligned_bounding_box()

        self.center = bbox.get_center()
        extent = bbox.get_extent()
        self.radius = max(extent) * 1.5
        self.scene.setup_camera(60.0, bbox, self.center)
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
