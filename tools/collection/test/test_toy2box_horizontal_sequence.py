# Copyright (c) 2026, The Isaac Lab Project Developers.
# All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
"""Check both horizontal-grip orders and their nominal pose constraints."""

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


auto = load("horizontal_auto_test", "record_toy2box_auto.py")
motion_module = load("horizontal_motion_test", "toy2box_motion_variation.py")
manual = load("horizontal_manual_test", "toy2box_manual_sequence.py")
STRATEGIES = ["horizontal_descend_first", "horizontal_xy_first"]


def state():
    return {
        "eef_pos": np.array([0.9, -0.2, 0.93]), "eef_quat": np.array([1., 0., 0., 0.]),
        "toy_truck_positions": np.array([0.65, -0.25, 0.38]),
        "toy_truck_orientations": np.array([1., 0., 0., 0.]),
        "box_positions": np.array([0.92, 0.05, 0.50]), "box_orientations": np.array([1., 0., 0., 0.]),
        "truck_bottom_z": 0.35, "box_top_z": 0.64, "box_bottom_z": 0.40, "opening_margin": -0.1,
    }


def examples():
    return [
        auto.GraspExample("side", 0, np.array([-0.035, -0.02, 0.003]), Rotation.from_euler("y", 1.55)),
        auto.GraspExample("top", 0, np.array([0.0, 0.0, -0.03]), Rotation.from_euler("x", np.pi)),
    ]


@pytest.mark.parametrize("yaw", [-3., -1., 0., 1.5, 3.])
def test_horizontal_grasp_levels_approach_axis_and_preserves_demonstrated_direction(yaw):
    reference = Rotation.from_euler("z", yaw) * Rotation.from_euler("y", 1.5)
    result = auto.horizontal_grasp_rotation(reference)
    direction = reference.as_matrix()[:, 2].copy()
    direction[2] = 0
    direction /= np.linalg.norm(direction)
    np.testing.assert_allclose(result.apply([0, 0, 1]), direction, atol=1e-12)
    assert result.as_matrix()[2, 2] == pytest.approx(0, abs=1e-12)


def test_nonzero_approach_tilt_is_not_a_supported_setting():
    with pytest.raises(TypeError):
        auto.ControllerConfig(horizontal_downward_tilt_deg=15)


def test_horizontal_approach_is_level_even_when_truck_is_tipped():
    obs = state()
    q = Rotation.from_euler("xyz", [.1, -.2, .7]).as_quat()
    obs["toy_truck_orientations"] = q[[3, 0, 1, 2]]
    _, _, rot = auto.geometric_side_grasp(obs, auto.ControllerConfig(), Rotation.identity())
    assert rot.as_matrix()[2, 2] == pytest.approx(0, abs=1e-12)
    assert rot.as_matrix()[2, 1] == pytest.approx(0, abs=1e-12)


def test_reach_check_accounts_for_horizontal_tool_length():
    rot = Rotation.from_euler("y", np.pi / 2)
    margin = auto.wrist_reach_margin(np.array([.7, 0, 0]), rot, np.zeros(3), np.array([0, 0, .2]), .6)
    assert margin == pytest.approx(.1)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_unreachable_horizontal_goal_is_rejected_before_any_motion(strategy):
    obs = state()
    obs.update(shoulder_pos=np.array([.304, -.213, 1.099]),
               wrist_to_tcp=np.array([0, 0, .227]), arm_reach=.6835)
    ctrl = auto.Toy2BoxController(examples(), auto.ControllerConfig(), strategy=strategy)
    ctrl.phase_time = 1.
    action = ctrl.action(obs, .05)
    assert "outside arm reach" in ctrl.failure
    np.testing.assert_array_equal(action, np.zeros(7))
    assert ctrl.phase == "settle" and not ctrl.lifted and not ctrl.released


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_horizontal_modes_use_geometry_and_keep_the_closing_axis_horizontal(strategy):
    ctrl = auto.Toy2BoxController(examples(), auto.ControllerConfig(), strategy=strategy)
    ctrl.choose_grasp(state())
    assert ctrl.reference is None
    assert ctrl.grasp_rot.as_matrix()[2, 2] == pytest.approx(0, abs=1e-12)
    assert ctrl.grasp_rot.as_matrix()[2, 1] == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_rotation_stage_sends_no_translation_commands(strategy):
    ctrl = auto.Toy2BoxController(examples(), auto.ControllerConfig(), strategy=strategy)
    ctrl.phase = "orient"
    position, rotation = ctrl.project_errors(np.array([0.1, -0.1, 0.1]), np.array([0.2, -0.3, 0.1]))
    np.testing.assert_array_equal(position, np.zeros(3))
    np.testing.assert_array_equal(rotation, [0.2, -0.3, 0.1])


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("phase,expected", [
    ("pre_descend", [0, 0, 0.1]), ("pre_xy", [0.1, 0.1, 0]),
    ("approach_xy", [0.1, 0.1, 0]), ("descend", [0, 0, 0.1]),
    ("lift", [0, 0, 0.1]), ("transfer", [0.1, 0.1, 0]), ("close", [0, 0, 0]),
])
def test_horizontal_translation_stages_mask_other_command_axes(strategy, phase, expected):
    ctrl = auto.Toy2BoxController(examples(), auto.ControllerConfig(), strategy=strategy)
    ctrl.phase = phase
    position, rotation = ctrl.project_errors(np.full(3, 0.1), np.full(3, 0.2))
    np.testing.assert_array_equal(position, expected)
    np.testing.assert_array_equal(rotation, [0, 0, 0])


@pytest.mark.parametrize("strategy,phase", [(STRATEGIES[0], "approach_xy"), (STRATEGIES[1], "descend")])
def test_wrong_grasp_orientation_fails_before_gripper_closes(strategy, phase):
    obs = state()
    ctrl = auto.Toy2BoxController(examples(), auto.ControllerConfig(), strategy=strategy)
    ctrl.choose_grasp(obs)
    obs["eef_pos"] = ctrl.grasp_pos.copy()
    ctrl.target_pos, ctrl.target_rot = ctrl.grasp_pos.copy(), ctrl.grasp_rot
    ctrl.phase = phase
    action = ctrl.action(obs, 0.05)
    assert ctrl.failure and "orientation lost" in ctrl.failure
    assert ctrl.phase != "close" and action[6] >= 0


@pytest.mark.parametrize("strategy,phase", [(STRATEGIES[0], "approach_xy"), (STRATEGIES[1], "descend")])
@pytest.mark.parametrize("deviation,can_close", [(0.004, True), (0.006, False)])
def test_grip_respects_numerical_tolerance_around_zero_tilt(strategy, phase, deviation, can_close):
    obs = state()
    ctrl = auto.Toy2BoxController(examples(), auto.ControllerConfig(), strategy=strategy)
    ctrl.choose_grasp(obs)
    obs["eef_pos"] = ctrl.grasp_pos.copy()
    q = (Rotation.from_rotvec([deviation, 0, 0]) * ctrl.grasp_rot).as_quat()
    obs["eef_quat"] = q[[3, 0, 1, 2]]
    ctrl.target_pos, ctrl.target_rot = ctrl.grasp_pos.copy(), ctrl.grasp_rot
    ctrl.phase = phase
    action = ctrl.action(obs, .05)
    assert (ctrl.phase == "close") == can_close
    assert (action[6] < 0) == can_close
    assert bool(ctrl.failure) != can_close


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("seed", [0, 42, 101])
def test_feedback_trial_keeps_requested_goal_order_and_releases_after_clearance(strategy, seed):
    cfg = auto.ControllerConfig()
    motion = motion_module.MotionVariation(seed, motion_module.MotionVariationConfig(
        position_offset=0, rotation_offset=0, idle_tail_seconds=cfg.release_seconds,
    ))
    ctrl = auto.Toy2BoxController(examples(), cfg, strategy=strategy, motion=motion)
    obs = state()
    phases, goals, actions, offset = [], {}, [], None
    for _ in range(1800):
        action = ctrl.action(obs, 0.05)
        assert ctrl.failure is None, ctrl.failure
        motion.observe_action(action, 0.05)
        actions.append(action)
        if not phases or phases[-1] != ctrl.phase:
            phases.append(ctrl.phase)
            goals[ctrl.phase] = (ctrl.target_pos.copy(), ctrl.target_rot)
        if action[6] < 0 and offset is None:
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
            assert obs["truck_bottom_z"] >= obs["box_top_z"] + cfg.transport_clearance - cfg.position_tolerance
        if ctrl.phase == "wait":
            break
    else:
        pytest.fail("Horizontal sequence did not finish")
    prefix = (["pre_descend", "orient", "approach_xy"] if strategy == STRATEGIES[0]
              else ["pre_xy", "orient", "descend"])
    assert phases == ["settle", *prefix, "close", "lift", "transfer", "release", "wait"]
    assert np.linalg.norm(goals["orient"][0] - goals[prefix[0]][0]) < cfg.position_tolerance
    assert goals["orient"][1].as_matrix()[2, 2] == pytest.approx(0, abs=1e-12)
    if strategy == STRATEGIES[0]:
        np.testing.assert_array_equal(goals["pre_descend"][0][:2], state()["eef_pos"][:2])
        assert goals["approach_xy"][0][2] == goals["orient"][0][2]
    else:
        assert goals["pre_xy"][0][2] == state()["eef_pos"][2]
        np.testing.assert_array_equal(goals["descend"][0][:2], goals["orient"][0][:2])
    assert ctrl.lifted and ctrl.released and auto.success_ready(ctrl, True)
    idle = (np.asarray(actions)[:, :6] == 0).all(1).mean()
    assert 0.18 <= idle <= 0.23


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_horizontal_planner_does_not_misclassify_tipped_object_reference_frames(strategy):
    ctrl = auto.Toy2BoxController(examples()[1:], auto.ControllerConfig(), strategy=strategy)
    ctrl.phase_time = 1.0
    action = ctrl.action(state(), 0.05)
    assert ctrl.failure is None
    assert ctrl.reference is None
    assert ctrl.phase in ("pre_descend", "pre_xy")
    assert action[6] == 1
    assert not ctrl.lifted and not ctrl.released


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_whole_manual_sequence_has_the_requested_first_three_rows(strategy):
    ctrl = auto.Toy2BoxController(examples(), auto.ControllerConfig(), strategy=strategy)
    obs = state()
    ctrl.choose_grasp(obs)
    steps, _ = manual.build_sequence(obs, ctrl.grasp_pos, ctrl.grasp_rot, ctrl.cfg,
                                     0.005, 0.025, strategy=strategy)
    expected = (["Descend to side-grasp height", "Align gripper rotation", "Move XY to side grasp"]
                if strategy == STRATEGIES[0] else
                ["Move XY above side grasp", "Align gripper rotation", "Descend to side-grasp height"])
    assert [step.name for step in steps[:3]] == expected
    assert len(steps) == 8
    assert steps[3].name == "Close gripper" and steps[6].name == "Open gripper"
    assert "horizontal" in steps[1].note
    achieved = Rotation.identity()
    for key, count in steps[1].keys:
        axis, sign = auto.KEY_MOTION[key]
        delta = np.zeros(3)
        delta[axis - 3] = sign * count * 0.025
        achieved = Rotation.from_euler("XYZ", delta) * achieved
    assert (achieved * ctrl.grasp_rot.inv()).magnitude() < 0.04
