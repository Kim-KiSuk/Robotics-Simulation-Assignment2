# Copyright (c) 2026, The Isaac Lab Project Developers.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
"""Check the staged collection rule, including axes, grasp, clearance and opening."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


auto = load("vertical_auto_test", "record_toy2box_auto.py")
variation = load("vertical_variation_test", "toy2box_motion_variation.py")
sequence = load("vertical_manual_test", "toy2box_manual_sequence.py")


def initial_state():
    return {
        "eef_pos": np.array([0.9, -0.2, 0.93]), "eef_quat": np.array([1., 0., 0., 0.]),
        "toy_truck_positions": np.array([0.65, -0.25, 0.38]),
        "toy_truck_orientations": np.array([1., 0., 0., 0.]),
        "box_positions": np.array([0.92, 0.05, 0.50]), "box_orientations": np.array([1., 0., 0., 0.]),
        "truck_bottom_z": 0.35, "box_top_z": 0.64, "box_bottom_z": 0.40, "opening_margin": -0.1,
    }


def controller(seed=42, strategy="vertical_first"):
    cfg = auto.ControllerConfig()
    ref = auto.GraspExample("demo_0", 0, np.array([0.02, 0.0, -0.02]),
                            Rotation.from_euler("XYZ", [2.8, 0.3, 0.7]))
    motion = variation.MotionVariation(seed, variation.MotionVariationConfig(
        position_offset=0, rotation_offset=0, idle_tail_seconds=cfg.release_seconds,
    ))
    return auto.Toy2BoxController([ref], cfg, motion=motion, strategy=strategy), motion


@pytest.mark.parametrize("yaw", [-3.1, -0.8, 0.0, 1.4, 3.1])
def test_downward_grasp_preserves_yaw_and_chooses_nearest_finger_symmetry(yaw):
    ref = Rotation.from_euler("XYZ", [2.8, 0.3, yaw])
    current = Rotation.from_euler("XYZ", [1.7, -0.5, 1.2])
    aligned = auto.downward_grasp_rotation(ref, current)
    np.testing.assert_allclose(aligned.apply([0, 0, 1]), [0, 0, -1], atol=1e-12)
    projected_x = ref.as_matrix()[:2, 0]
    projected_x /= np.linalg.norm(projected_x)
    assert abs(np.dot(aligned.as_matrix()[:2, 0], projected_x)) == pytest.approx(1.0)
    other = aligned * Rotation.from_rotvec([0, 0, np.pi])
    assert (aligned * current.inv()).magnitude() <= (other * current.inv()).magnitude() + 1e-12


@pytest.mark.parametrize("phase,axes", [
    ("orient", (3, 4, 5)), ("approach_xy", (0, 1)), ("descend", (2,)),
    ("safe_raise", (2,)), ("lift", (2,)), ("transfer", (0, 1)),
    ("settle", ()), ("close", ()), ("release", ()), ("wait", ()),
])
def test_each_phase_only_emits_its_designated_motion_axes(phase, axes):
    ctrl, _ = controller()
    ctrl.phase = phase
    errors = np.r_[ctrl.project_errors(np.ones(3), np.ones(3))]
    assert set(np.flatnonzero(errors)) == set(axes)


def run_kinematic_trial(seed, attached_grasp=True, strategy="vertical_first"):
    ctrl, motion = controller(seed, strategy)
    obs = initial_state()
    phases, actions, offset = [], [], None
    for _ in range(1800):
        action = ctrl.action(obs, 0.05)
        if ctrl.failure:
            break
        motion.observe_action(action, 0.05)
        actions.append(action)
        if not phases or phases[-1] != ctrl.phase:
            phases.append(ctrl.phase)
        if action[6] < 0 and offset is None and attached_grasp:
            offset = obs["eef_pos"] - obs["toy_truck_positions"]
        if action[6] > 0:
            offset = None
        obs["eef_pos"] += 0.25 * action[:3]
        quat = (Rotation.from_rotvec(0.6 * action[3:6]) * auto.rotation(obs["eef_quat"])).as_quat()
        obs["eef_quat"] = quat[[3, 0, 1, 2]]
        if offset is not None:
            obs["toy_truck_positions"] = obs["eef_pos"] - offset
        obs["truck_bottom_z"] = obs["toy_truck_positions"][2] - 0.03
        obs["opening_margin"] = 0.025 - np.max(np.abs(obs["toy_truck_positions"][:2] - obs["box_positions"][:2]))
        if ctrl.phase == "transfer":
            minimum_bottom = obs["box_top_z"] + ctrl.cfg.transport_clearance - ctrl.cfg.position_tolerance
            assert obs["truck_bottom_z"] >= minimum_bottom
        if ctrl.phase == "release":
            assert obs["opening_margin"] >= 0
            assert np.linalg.norm(action[:6]) == 0
            assert action[6] == 1
        if ctrl.phase == "wait":
            break
    return ctrl, motion, phases, np.asarray(actions)


@pytest.mark.parametrize("seed", [0, 7, 42, 101])
@pytest.mark.parametrize("strategy", ["vertical_first", "vertical_descend_first", "vertical_xy_first"])
def test_full_staged_rule_finishes_with_release_and_keeps_idle_near_twenty_percent(seed, strategy):
    ctrl, motion, phases, actions = run_kinematic_trial(seed, strategy=strategy)
    assert ctrl.failure is None
    prefix = {"vertical_first": ["orient", "approach_xy", "descend"],
              "vertical_descend_first": ["clear_box", "pre_descend", "orient", "approach_xy"],
              "vertical_xy_first": ["pre_xy", "orient", "descend"]}[strategy]
    assert phases == ["settle", *prefix, "close", "lift", "transfer", "release", "wait"]
    np.testing.assert_allclose(ctrl.grasp_rot.apply([0, 0, 1]), [0, 0, -1], atol=1e-12)
    assert ctrl.lifted and ctrl.released
    actual_idle = (actions[:, :6] == 0).all(1).mean()
    assert motion.export()["actual_idle_fraction"] == actual_idle
    assert 0.18 <= actual_idle <= 0.23
    assert auto.success_ready(ctrl, True)
    assert not auto.success_ready(ctrl, False)


def test_failed_grasp_does_not_advance_to_box_or_release():
    ctrl, _, phases, _ = run_kinematic_trial(101, attached_grasp=False)
    assert ctrl.failure == "truck did not lift with the gripper"
    assert "transfer" not in phases and "release" not in phases
    assert not auto.success_ready(ctrl, True)


@pytest.mark.parametrize("phase", ["orient", "descend"])
def test_xy_first_corrects_drift_before_rotating_or_gripping(phase):
    ctrl, _ = controller(strategy="vertical_xy_first")
    ctrl.motion = None
    obs = initial_state()
    ctrl.choose_grasp(obs)
    ctrl.phase = phase
    ctrl.target_pos = ctrl.grasp_pos.copy()
    if phase == "orient":
        ctrl.target_pos[2] = .93
    ctrl.target_rot = ctrl.grasp_rot
    q = ctrl.grasp_rot.as_quat()
    obs["eef_quat"] = q[[3, 0, 1, 2]]
    obs["eef_pos"] = ctrl.target_pos + [.15, -.05, 0]
    action = ctrl.action(obs, .05)
    assert ctrl.phase == phase and ctrl.failure is None
    assert action[0] < 0 and action[1] > 0 and action[6] > 0
    obs["eef_pos"] = ctrl.target_pos.copy()
    action = ctrl.action(obs, .05)
    assert ctrl.phase == ("descend" if phase == "orient" else "close")


@pytest.mark.parametrize("yaw", [0, .4, -.7])
def test_first_rule_clears_the_whole_box_footprint_before_lowering(yaw):
    ctrl, _ = controller(strategy="vertical_descend_first")
    ctrl.motion = None
    obs = initial_state()
    q = Rotation.from_euler("z", yaw).as_quat()
    obs["box_orientations"] = q[[3, 0, 1, 2]]
    obs["box_local_bounds"] = np.array([[-.15, -.1, -.1], [.15, .1, .14]])
    ctrl.phase_time = 1.
    action = ctrl.action(obs, .05)
    assert ctrl.phase == "clear_box" and action[2] == 0
    assert ctrl.target_pos[2] == obs["eef_pos"][2]
    lower, upper = obs["box_local_bounds"]
    corners = np.array(list(auto.product(*zip(lower, upper))))
    world = auto.rotation(obs["box_orientations"]).apply(corners) + obs["box_positions"]
    assert np.all(ctrl.target_pos[:2] <= world[:, :2].min(0) - ctrl.cfg.box_staging_distance + 1e-12)
    obs["eef_pos"] = ctrl.target_pos.copy()
    ctrl.action(obs, .05)
    assert ctrl.phase == "pre_descend"


@pytest.mark.parametrize("strategy", ["vertical_first", "vertical_descend_first", "vertical_xy_first"])
def test_vertical_strategy_uses_a_top_down_reference_instead_of_flattening_a_side_grasp(strategy):
    cfg = auto.ControllerConfig()
    side = auto.GraspExample("side", 0, np.array([0.04, 0.0, 0.02]), Rotation.identity())
    top = auto.GraspExample("top", 0, np.array([0.0, 0.0, -0.03]), Rotation.from_euler("x", np.pi))
    ctrl = auto.Toy2BoxController([side, top], cfg, strategy=strategy)
    ctrl.choose_grasp(initial_state())
    assert ctrl.reference.episode == "top"
    np.testing.assert_allclose(ctrl.grasp_rot.apply([0, 0, 1]), [0, 0, -1], atol=1e-12)


def test_vertical_controller_reserves_height_before_xy_transport():
    ctrl, _ = controller()
    obs = initial_state()
    ctrl.choose_grasp(obs)
    ctrl.phase, ctrl.phase_time = "close", ctrl.cfg.grip_seconds
    ctrl.action(obs, 0.05)
    planned_bottom = ctrl.target_pos[2] - ctrl.held_offset[2] + obs["truck_bottom_z"] - obs["toy_truck_positions"][2]
    required = obs["box_top_z"] + ctrl.cfg.transport_clearance + ctrl.cfg.transfer_height_reserve
    assert planned_bottom >= required - 1e-12


@pytest.mark.parametrize("strategy", ["vertical_first", "vertical_descend_first", "vertical_xy_first"])
def test_full_manual_plan_starts_with_rotation_and_has_no_extra_lowering_or_retreat(strategy):
    ctrl, _ = controller(strategy=strategy)
    obs = initial_state()
    ctrl.choose_grasp(obs)
    steps, _ = sequence.build_sequence(obs, ctrl.grasp_pos, ctrl.grasp_rot, ctrl.cfg,
                                       0.005, 0.025, strategy=strategy)
    prefix = {"vertical_first": ["Align gripper rotation", "Move XY above truck", "Descend to grasp"],
              "vertical_descend_first": ["Move XY clear of box", "Descend to grasp height", "Align gripper rotation", "Move XY to truck"],
              "vertical_xy_first": ["Move XY above truck", "Align gripper rotation", "Descend to grasp"]}[strategy]
    assert [step.name for step in steps] == [*prefix, "Close gripper",
        "Lift above box rim", "Move XY above box", "Open gripper", "Wait for success / reset",
    ]
    if strategy == "vertical_first":
        np.testing.assert_array_equal(steps[0].target_pos, obs["eef_pos"])
        assert steps[1].target_pos[2] == obs["eef_pos"][2]


@pytest.mark.parametrize("manual", [False, True])
def test_vertical_cli_defaults_keep_idle_budget_without_enabling_it_for_manual_control(tmp_path, manual):
    args = auto.create_parser().parse_args([
        "--reference_dataset", str(tmp_path / "reference.hdf5"),
        "--dataset_file", str(tmp_path / "new.hdf5"),
    ] + (["--full_sequence"] if manual else []))
    args.headless = False
    auto.validate_args(args)
    assert args.collection_strategy == "vertical_first"
    assert args.motion_style == ("standard" if manual else "varied")
    assert args.target_idle_fraction == 0.21
