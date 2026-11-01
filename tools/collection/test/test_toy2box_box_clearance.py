# Copyright (c) 2026, The Isaac Lab Project Developers.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
"""Check conservative clearance for rotated arm/housing and box bounds."""

import importlib.util
from itertools import product
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest
from scipy.spatial.transform import Rotation


spec = importlib.util.spec_from_file_location(
    "box_clearance_test", Path(__file__).parents[1] / "toy2box_box_clearance.py")
clearance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clearance)


@pytest.mark.parametrize("offset,expected", [(2, 1), (1.03, .03), (1, 0), (.8, -.2)])
def test_contact_and_near_contact_do_not_pass_as_safe_clearance(offset, expected):
    cube = np.array(list(product([-.5, .5], repeat=3)))
    actual = clearance.obb_separation(cube, np.eye(3), cube + [offset, 0, 0], np.eye(3))
    assert actual == pytest.approx(expected)


def test_rotated_wrist_housing_uses_oriented_bounds():
    local = np.array(list(product([-1, 1], [-.05, .05], [-.05, .05])))
    rot = Rotation.from_euler("z", np.pi / 4).as_matrix()
    a = local @ rot.T
    b = a + rot[:, 1] * .3
    assert np.all(np.minimum(a.max(0), b.max(0)) > np.maximum(a.min(0), b.min(0)))
    assert clearance.obb_separation(a, rot, b, rot) == pytest.approx(.2)


def test_gripper_above_opening_is_safe_only_with_vertical_clearance():
    box = np.array(list(product([-.15, .15], [-.1, .1], [0, .3])))
    hand = np.array(list(product([-.05, .05], [-.05, .05], [.34, .5])))
    assert clearance.obb_separation(hand, np.eye(3), box, np.eye(3)) == pytest.approx(.04)
    hand[:, 2] -= .05
    assert clearance.obb_separation(hand, np.eye(3), box, np.eye(3)) < 0


def test_contact_sensor_uses_one_box_and_individual_link_filters(monkeypatch):
    module = ModuleType("isaaclab.sensors")
    module.ContactSensorCfg = lambda **kwargs: SimpleNamespace(**kwargs)
    monkeypatch.setitem(sys.modules, "isaaclab.sensors", module)
    cfg = SimpleNamespace(decimation=3, scene=SimpleNamespace(
        box=SimpleNamespace(prim_path="{ENV_REGEX_NS}/Box", spawn=SimpleNamespace()),
    ))
    clearance.configure_box_contact_sensor(cfg)
    sensor = cfg.scene.box_robot_contact
    assert sensor.prim_path == cfg.scene.box.prim_path
    assert sensor.history_length == 4 and sensor.update_period == 0
    assert not cfg.scene.lazy_sensor_update
    assert len(sensor.filter_prim_paths_expr) == 18
    assert all("*" not in pattern for pattern in sensor.filter_prim_paths_expr)
