# Copyright (c) 2026, The Isaac Lab Project Developers.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
"""Independent arm/housing clearance and box-contact checks for collection."""

from itertools import product

import numpy as np
from scipy.spatial.transform import Rotation


def rotation(quat):
    return Rotation.from_quat(np.asarray(quat)[[1, 2, 3, 0]])


def obb_separation(corners_a, rotation_a, corners_b, rotation_b):
    """Conservative clearance bound from the 15 separating axes of two OBBs.

    Positive values prove separation. A nonpositive result means the bounding
    volumes overlap; it does not claim the underlying nonconvex meshes touch.
    """
    axes = [*rotation_a.T, *rotation_b.T]
    axes.extend(np.cross(a, b) for a in rotation_a.T for b in rotation_b.T)
    gaps = []
    for axis in axes:
        norm = np.linalg.norm(axis)
        if norm < 1e-8:
            continue
        a, b = corners_a @ (axis / norm), corners_b @ (axis / norm)
        gaps.append(max(b.min() - a.max(), a.min() - b.max()))
    return float(max(gaps))


def configure_box_contact_sensor(cfg):
    """Observe box-to-robot contacts at physics frequency without changing collisions."""
    from isaaclab.sensors import ContactSensorCfg

    cfg.scene.box.spawn.activate_contact_sensors = True
    cfg.scene.lazy_sensor_update = False
    names = [f"Link{i}_r" for i in range(1, 8)] + ["right_base_link"]
    names += [f"right_{side}_{part}_Link" for side in ("Right", "Left")
              for part in ("00", "01", "Support", "Pad", "2")]
    cfg.scene.box_robot_contact = ContactSensorCfg(
        prim_path=cfg.scene.box.prim_path,
        update_period=0.0,
        history_length=cfg.decimation + 1,
        filter_prim_paths_expr=["{ENV_REGEX_NS}/Robot/" + name for name in names],
        debug_vis=False,
    )


class BoxClearanceGuard:
    """Monitor geometry and contacts without changing the task's motion controller."""

    def __init__(self, env, box_corners, margin=0.025):
        import omni.usd
        from pxr import Usd, UsdGeom

        self.env, self.robot, self.margin = env, env.scene["robot"], margin
        self.box_corners = box_corners
        stage = omni.usd.get_context().get_stage()
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
        link_paths = self.robot.root_physx_view.link_paths[0]
        self.bodies = []
        for index, name in enumerate(self.robot.body_names):
            if not (name.startswith("right_") or (name.startswith("Link") and name.endswith("_r"))):
                continue
            prim = stage.GetPrimAtPath(link_paths[index])
            if not prim.IsValid():
                continue
            bounds = cache.ComputeUntransformedBound(prim).ComputeAlignedRange()
            if bounds.IsEmpty():
                continue
            lower, upper = np.array(bounds.GetMin()), np.array(bounds.GetMax())
            if np.any(upper - lower < 1e-5):
                continue
            self.bodies.append((index, name, np.array(list(product(*zip(lower, upper))))))
        if not self.bodies:
            raise RuntimeError("No arm/gripper geometry found for the box clearance check")
        self.reset_stats()

    def reset_stats(self):
        self.minimum_separation = float("inf")
        self.closest_body = None
        self.maximum_contact_force = 0.0

    def gripper_bounds_in_tcp(self):
        """Include the asymmetric wrist/camera housing when choosing finger symmetry."""
        tcp = self.robot.body_names.index("right_gripper_center")
        positions = self.robot.data.body_pos_w[0].cpu().numpy()
        quats = self.robot.data.body_quat_w[0].cpu().numpy()
        inverse = rotation(quats[tcp]).inv()
        points = []
        for index, name, corners in self.bodies:
            if name.startswith("right_"):
                world = rotation(quats[index]).apply(corners) + positions[index]
                points.append(inverse.apply(world - positions[tcp]))
        points = np.concatenate(points)
        return np.array([points.min(0) - .005, points.max(0) + .005])

    def check(self):
        box = self.env.scene["box"].data
        pos, quat = box.root_pos_w[0].cpu().numpy(), box.root_quat_w[0].cpu().numpy()
        box_rot = rotation(quat).as_matrix()
        box_points = self.box_corners @ box_rot.T + pos
        positions = self.robot.data.body_pos_w[0].cpu().numpy()
        quats = self.robot.data.body_quat_w[0].cpu().numpy()
        separation, closest = float("inf"), None
        for index, name, corners in self.bodies:
            rot = rotation(quats[index]).as_matrix()
            gap = obb_separation(corners @ rot.T + positions[index], rot, box_points, box_rot)
            if gap < separation:
                separation, closest = gap, name
        forces = self.env.scene["box_robot_contact"].data.force_matrix_w_history
        contact = float(forces.norm(dim=-1).max().item())
        if separation < self.minimum_separation:
            self.minimum_separation, self.closest_body = separation, closest
        self.maximum_contact_force = max(self.maximum_contact_force, contact)
        if contact > 0.05:
            return f"robot/box contact: {contact:.3f} N"
        if separation < self.margin:
            return f"box clearance too small: {closest}, {separation:.3f} m"
        return None

    def export(self):
        return {
            "required_clearance_m": self.margin,
            "minimum_bound_separation_m": self.minimum_separation,
            "closest_body": self.closest_body,
            "maximum_box_robot_contact_force_n": self.maximum_contact_force,
            "watched_bodies": [body[1] for body in self.bodies],
            "gripper_bounds_in_tcp": self.gripper_bounds_in_tcp().tolist(),
        }
