# Copyright (c) 2026, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
r"""Collect Toy2Box demonstrations using a feedback controller and successful grasp examples.

Run from IsaacLab_RS in the lerobot-arena environment::

    ./isaaclab.sh -p scripts/tools/record_toy2box_auto.py \
        --reference_dataset /home/kisuk/toy/toy2box_agibot.hdf5 \
        --dataset_file ./datasets/toy2box_agibot_auto.hdf5 --num_demos 20

Use --inspect_reference to validate the source dataset without launching Isaac Sim.
Use --manual_guidance to show recommended key counts in a GUI window and terminal;
only the person's keyboard input moves the robot in that mode. Automatic timeout
and stall resets are disabled while following guidance. One press/release adds one
fixed pose increment, irrespective of how long the key is down. K toggles the gripper.
Use --full_sequence for an entirely manual session with top/left viewports and
the complete planned sequence shown at once. N highlights the next row only.
Use --motion_style varied for seeded speed changes, brief pauses, and small
intermediate corrections in automatic collection. --target_idle_fraction defaults
to 0.21 and budgets actual zero-motion frames across the episode, with a small
seeded variation per attempt. These are still scripted demos.
The default --collection_strategy vertical_first separates rotation, XY travel,
vertical descent, grip, vertical lift, box travel, and release. The gripper's
local +Z axis is aligned downward. Use reference for the original controller.
Use vertical_descend_first for safe XY staging outside the box followed by
Z/rotation/XY, or vertical_xy_first for XY/rotation/Z. Both then grip/lift/travel/
release with downward grasping. The first rule monitors full arm/wrist geometry
and box-to-robot contacts, and rejects attempts below 2.5 cm body clearance.
The horizontal_descend_first and horizontal_xy_first strategies use, respectively,
Z/rotation/XY and XY/rotation/Z before gripping. Their side-grasp targets come from
the truck bounds; both the approach and finger-closing axes are horizontal by
default. The approach target is fixed at exactly zero tilt. These strategies
require physical validation at the chosen poses.
The reference is read only. Outputs must be new files. In the GUI, R discards the
current attempt and P pauses/resumes. Ctrl+C stops with completed demos preserved.
After collection ends, the GUI keeps the reset scene and result visible until
you close the result window. Use --exit_on_finish for immediate exit; headless
runs always exit when collection ends.
Actions have the same seven components as the keyboard in relative pose mode.
This is a scripted demonstrator, not a trained policy or an open-loop key replay.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path

import h5py
import numpy as np
from scipy.spatial.transform import Rotation

TASK = "Isaac-Place-Toy2Box-Agibot-Right-Arm-RmpFlow-v0"
POSE_KEYS = (
    "eef_pos", "eef_quat", "toy_truck_positions", "toy_truck_orientations", "box_positions", "box_orientations"
)
HORIZONTAL_STRATEGIES = {"horizontal_descend_first", "horizontal_xy_first"}
DOWNWARD_STRATEGIES = {"vertical_first", "vertical_descend_first", "vertical_xy_first"}
DESCEND_FIRST_STRATEGIES = {"vertical_descend_first", "horizontal_descend_first"}
XY_FIRST_STRATEGIES = {"vertical_xy_first", "horizontal_xy_first"}
STAGED_STRATEGIES = DOWNWARD_STRATEGIES | HORIZONTAL_STRATEGIES
COLLECTION_STRATEGIES = (
    "vertical_first", "vertical_descend_first", "vertical_xy_first",
    "horizontal_descend_first", "horizontal_xy_first", "reference",
)


KEY_BINDINGS = (("W", "S"), ("A", "D"), ("Q", "E"), ("Z", "X"), ("T", "G"), ("C", "V"))
KEY_MOTION = {key: (axis, sign) for axis, pair in enumerate(KEY_BINDINGS) for key, sign in zip(pair, (1, -1))}


class TapQueue:
    """Count key-down edges, ignoring repeat events until a physical key-up."""

    def __init__(self):
        self.down = set()
        self.pending = deque()

    def press(self, key: str) -> bool:
        if key in self.down:
            return False
        self.down.add(key)
        if key in KEY_MOTION or key == "K":
            self.pending.append(key)
        return True

    def release(self, key: str):
        self.down.discard(key)

    def pop(self) -> list[str]:
        result = list(self.pending)
        self.pending.clear()
        return result


def create_tap_keyboard(base_class, cfg):
    """Reuse Isaac Lab's keyboard subscription, with discrete press semantics."""
    import carb

    class TapKeyboard(base_class):
        def __init__(self, cfg):
            self.taps = TapQueue()
            super().__init__(cfg)

        def _on_keyboard_event(self, event, *args, **kwargs):
            key = event.input.name
            if event.type == carb.input.KeyboardEventType.KEY_PRESS:
                if self.taps.press(key) and key in self._additional_callbacks:
                    self._additional_callbacks[key]()
            elif event.type == carb.input.KeyboardEventType.KEY_RELEASE:
                self.taps.release(key)
            return True

        def pop_presses(self):
            return self.taps.pop()

        def reset(self):
            super().reset()
            # Preserve held-key state: reset must not turn a long press into a new tap.
            self.taps.pending.clear()

    return TapKeyboard(cfg)


def plan_key_count(position_error, rotation_error, pos_step: float, rot_step: float, batch_size: int):
    motion = np.r_[position_error, Rotation.from_rotvec(rotation_error).as_euler("XYZ")]
    counts = np.abs(motion) / np.array([pos_step] * 3 + [rot_step] * 3)
    axis = int(np.argmax(counts))
    count = int(math.floor(counts[axis] + 0.5))
    if count == 0:
        return None, 0
    return KEY_BINDINGS[axis][0 if motion[axis] > 0 else 1], min(count, batch_size)


class TapMotionController:
    """Each physical press adds one pose increment; the servo completes that move.

    Feedback commands track the user-selected pose between key events. A held key
    adds no further increments. Queued taps are spaced out to let the arm respond.
    """

    def __init__(self, pos_step: float, rot_step: float, settle_seconds: float):
        self.pos_step, self.rot_step = pos_step, rot_step
        self.settle_seconds = settle_seconds
        self.closed = False
        self.pending = deque()
        self.target_pos = self.target_rot = None
        self.since_tap = math.inf

    @property
    def busy(self):
        return bool(self.pending) or self.since_tap < self.settle_seconds

    def clear_motion(self, state):
        self.pending.clear()
        self.target_pos = state["eef_pos"].copy()
        self.target_rot = rotation(state["eef_quat"])
        self.since_tap = math.inf

    def action(self, state, presses: list[str], dt: float):
        if self.target_pos is None:
            self.clear_motion(state)
        self.pending.extend(key for key in presses if key in KEY_MOTION or key == "K")
        self.since_tap += dt
        if self.pending and self.since_tap >= self.settle_seconds:
            key = self.pending.popleft()
            if key == "K":
                self.closed = not self.closed
            else:
                axis, sign = KEY_MOTION[key]
                if axis < 3:
                    self.target_pos[axis] += sign * self.pos_step
                else:
                    delta = np.zeros(3)
                    delta[axis - 3] = sign * self.rot_step
                    self.target_rot = Rotation.from_euler("XYZ", delta) * self.target_rot
            self.since_tap = 0.0
        pos_error = self.target_pos - state["eef_pos"]
        rot_error = (self.target_rot * rotation(state["eef_quat"]).inv()).as_rotvec()
        return np.r_[limited(0.7 * pos_error, 0.025), limited(0.7 * rot_error, 0.05),
                     -1.0 if self.closed else 1.0].astype(np.float32)


class CountedKeyGuide:
    """Freeze a short count until it is entered, then replan from measured pose."""

    def __init__(self, pos_step: float, rot_step: float, batch_size: int):
        self.pos_step, self.rot_step, self.batch_size = pos_step, rot_step, batch_size
        self.phase = self.key = None
        self.remaining = self.total = 0

    def update(self, controller, state, advice, taps: TapMotionController, presses: list[str]) -> str:
        phase = controller.phase
        if phase != self.phase:
            self.phase, self.key, self.remaining = phase, None, 0
        for key in presses:
            if key == self.key and self.remaining:
                self.remaining -= 1
            elif key in KEY_MOTION or key == "K":
                # An unplanned input changes the goal estimate; re-evaluate after it settles.
                self.key, self.remaining = None, 0
        desired_closed = bool(advice[6] < 0)
        if self.remaining:
            return self.format(desired_closed)
        if taps.busy:
            return f"Wait for the arm to settle ({len(taps.pending)} queued taps).\nNext count follows automatically."
        if desired_closed != taps.closed:
            self.key, self.remaining, self.total = "K", 1, 1
        elif phase in ("settle", "close", "release", "wait"):
            self.key, self.remaining = None, 0
        else:
            pos_error = controller.target_pos - state["eef_pos"]
            rot_error = (controller.target_rot * rotation(state["eef_quat"]).inv()).as_rotvec()
            if hasattr(controller, "project_errors"):
                pos_error, rot_error = controller.project_errors(pos_error, rot_error)
            self.key, self.remaining = plan_key_count(
                pos_error, rot_error, self.pos_step, self.rot_step, self.batch_size
            )
            self.total = self.remaining
        return self.format(desired_closed)

    def format(self, desired_closed: bool):
        if self.key is None or not self.remaining:
            return "No key input needed. Waiting for the next phase."
        suffix = f" to {'CLOSE' if desired_closed else 'OPEN'}" if self.key == "K" else ""
        return (
            f"Tap {self.key} x {self.remaining}{suffix}\n"
            f"Remaining {self.remaining} / {self.total}. Release after each tap."
        )


class KeyboardGuideDisplay:
    """Display advice in a GUI window and a throttled terminal log."""

    def __init__(self, interval: float):
        import omni.ui as ui

        self.window = ui.Window("Toy2Box Keyboard Guide", width=520, height=230)
        with self.window.frame:
            with ui.VStack(spacing=8):
                ui.Label("MANUAL: tap and release once per count. R: reset | P: pause", word_wrap=True)
                self.label = ui.Label("Preparing guidance...", word_wrap=True)
                ui.Label("W/S X | A/D Y | Q/E Z | Z/X roll | T/G pitch | C/V yaw | K gripper", word_wrap=True)
        self.interval = interval
        self.last_text = None
        self.last_phase = None
        self.last_update = -math.inf

    def update(self, phase: str, hint: str):
        text = f"Phase: {phase}\n{hint}"
        now = time.monotonic()
        if phase != self.last_phase or (text != self.last_text and now - self.last_update >= self.interval):
            self.label.text = text
            print(f"[GUIDE] {phase}: {hint.replace(chr(10), ' | ')}")
            self.last_text, self.last_phase, self.last_update = text, phase, now

    def close(self):
        self.window.destroy()


class CollectionResultDisplay:
    """Keep the final outcome readable after the last reset."""

    def __init__(self, report, report_path, num_demos):
        import omni.ui as ui

        attempts = report["attempts"]
        reason = attempts[-1]["reason"] if attempts else "No attempt completed."
        self.window = ui.Window("Toy2Box Collection Result", width=650, height=310)
        with self.window.frame:
            with ui.VStack(spacing=10):
                ui.Label(f"Saved {report['successful_demos']} / {num_demos} demos | Attempts: {len(attempts)}")
                ui.Label(f"Last result: {reason}", word_wrap=True)
                if "outside arm reach" in reason:
                    ui.Label(
                        "The horizontal 0-degree target is unreachable. Adjust the grasp position or work height.",
                        word_wrap=True,
                    )
                ui.Label(f"Run log: {report_path}", word_wrap=True)
                ui.Label("Collection has ended. The reset scene stays visible; no new data is being recorded.",
                         word_wrap=True)
                ui.Button("Close result and exit", clicked_fn=self.dismiss)

    @property
    def visible(self):
        return self.window.visible

    def dismiss(self):
        self.window.visible = False

    def close(self):
        self.window.destroy()


def review_collection_result(env, simulation_app, report, report_path, num_demos, *, headless, exit_on_finish):
    """Render the final scene without stepping physics or recording extra frames."""
    if headless or exit_on_finish or not simulation_app.is_running():
        return
    display = CollectionResultDisplay(report, report_path, num_demos)
    print(f"[AUTO] Collection ended: {report['successful_demos']}/{num_demos} saved. "
          "The GUI stays open for review; close the result window or press Ctrl+C to exit.", flush=True)
    try:
        while simulation_app.is_running() and display.visible:
            env.sim.render()
            time.sleep(1 / 30)
    finally:
        display.close()


def height_limits(corners: np.ndarray, position: np.ndarray, quat: np.ndarray) -> tuple[float, float]:
    """Transform local geometry bounds using the live physics pose, not stale USD poses."""
    heights = rotation(quat).apply(corners)[:, 2] + position[2]
    return float(heights.min()), float(heights.max())


def opening_margin(box_corners: np.ndarray, truck_corners: np.ndarray, state: dict, inset: float) -> float:
    """Smallest XY clearance inside the box bounds, accounting for both rotations.

    Bounds describe the outer box. The inset reserves space for its walls.
    Positive means the entire truck footprint is inside that opening.
    """
    truck_points = rotation(state["toy_truck_orientations"]).apply(truck_corners)
    truck_points += state["toy_truck_positions"] - state["box_positions"]
    in_box = rotation(state["box_orientations"]).inv().apply(truck_points)
    lower = box_corners.min(axis=0)[:2] + inset
    upper = box_corners.max(axis=0)[:2] - inset
    return float(min((in_box[:, :2] - lower).min(), (upper - in_box[:, :2]).min()))


def success_ready(controller, task_success: bool) -> bool:
    """Use the task's success definition once an actual release has been commanded.

    A settled truck is below the box's origin in this asset. Do not impose an
    invented positive truck-to-box root height, or wait for an exact retreat pose.
    """
    return bool(controller.lifted and controller.released and task_success)


def read_local_bounds(env, name: str) -> np.ndarray:
    """Read geometry in the rigid body's frame once; physics supplies later poses."""
    import omni.usd
    from pxr import Gf, Usd, UsdGeom

    path = env.scene[name].root_physx_view.prim_paths[0]
    prim = omni.usd.get_context().get_stage().GetPrimAtPath(path)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    bounds = cache.ComputeUntransformedBound(prim).ComputeAlignedRange()
    if bounds.IsEmpty():
        raise ValueError(f"Cannot determine geometry bounds for {path}")
    corners = np.array(list(product(*zip(bounds.GetMin(), bounds.GetMax()))), dtype=float)
    # Untransformed bounds omit the root's own scale, whereas physics poses
    # contain position/orientation only. Include that scale in local corners.
    scale = np.array(Gf.Transform(UsdGeom.Xformable(prim).GetLocalTransformation()).GetScale())
    corners *= scale
    if not np.isfinite(corners).all() or np.any(np.ptp(corners, axis=0) <= 0):
        raise ValueError(f"Invalid geometry bounds for {path}")
    return corners


def reset_recording_instance(env):
    """Reset simulator, failed/saved episode buffer, and scene after every outcome."""
    env.sim.reset()
    env.recorder_manager.reset()
    observation, _ = env.reset()
    return observation


def rotation(quat: np.ndarray) -> Rotation:
    """Isaac Lab quaternions use wxyz; SciPy defaults to xyzw."""
    quat = np.asarray(quat)
    return Rotation.from_quat(quat[[1, 2, 3, 0]])


@dataclass
class GraspExample:
    episode: str
    step: int
    offset: np.ndarray
    orientation: Rotation


def load_grasps(path: Path) -> list[GraspExample]:
    """Extract the last successful grasp in each successful episode.

    A close command counts only if the truck rises >= 6 cm before the next
    opening. Failed close/open attempts in otherwise successful demos are ignored.
    Sample the pose once the truck is 3 cm above its pre-grasp height, rather
    than at the close command (the hand can still be moving while closing).
    Store the end-effector pose in the truck frame so it follows randomized yaw.
    """
    examples = []
    with h5py.File(path, "r") as dataset:
        env_args = json.loads(dataset["data"].attrs.get("env_args", "{}"))
        if env_args.get("env_name") != TASK:
            raise ValueError(f"Reference must be for {TASK}; got {env_args.get('env_name')!r}")
        for name, episode in dataset["data"].items():
            if not episode.attrs.get("success", False):
                continue
            actions = episode["actions"][:]
            obs = episode["obs"]
            if actions.ndim != 2 or actions.shape[1] != 7:
                raise ValueError(f"{name}: expected relative pose actions with shape (T, 7)")
            for key in POSE_KEYS:
                if key not in obs or len(obs[key]) != len(actions):
                    raise ValueError(f"{name}: missing or misaligned observation {key}")
            truck = obs["toy_truck_positions"][:]
            closed = actions[:, 6] < 0
            starts = np.flatnonzero(closed & np.r_[True, ~closed[:-1]])
            candidates = []
            for start in starts:
                openings = np.flatnonzero(~closed[start:])
                end = start + openings[0] if len(openings) else len(actions)
                if np.max(truck[start:end, 2]) - truck[start, 2] < 0.06:
                    continue
                grasp_step = int(start + np.flatnonzero(truck[start:end, 2] - truck[start, 2] >= 0.03)[0])
                truck_rot = rotation(obs["toy_truck_orientations"][grasp_step])
                offset = truck_rot.inv().apply(obs["eef_pos"][grasp_step] - truck[grasp_step])
                ee_rot = truck_rot.inv() * rotation(obs["eef_quat"][grasp_step])
                if not np.isfinite(offset).all() or np.linalg.norm(offset) > 0.12:
                    continue
                candidates.append(GraspExample(name, grasp_step, offset, ee_rot))
            if candidates:
                examples.append(candidates[-1])
    if not examples:
        raise ValueError("No successful close-and-lift examples found in the reference dataset")
    return examples


@dataclass
class ControllerConfig:
    approach_height: float = 0.14
    lift_height: float = 0.16
    transport_clearance: float = 0.16
    transfer_height_reserve: float = 0.04
    position_tolerance: float = 0.012
    horizontal_position_tolerance: float = 0.01
    horizontal_rotation_tolerance: float = 0.005
    horizontal_height_fraction: float = 0.75
    horizontal_grasp_inset: float = 0.035
    rotation_tolerance: float = 0.15
    max_translation: float = 0.025
    max_rotation: float = 0.05
    gain: float = 0.7
    settle_seconds: float = 0.5
    grip_seconds: float = 1.0
    release_seconds: float = 0.8
    phase_timeout: float = 15.0
    episode_timeout: float = 90.0
    stall_seconds: float = 5.0
    opening_inset: float = 0.015
    alignment_seconds: float = 0.25
    release_clearance: float = 0.04
    box_staging_distance: float = 0.20

    def clearance_staging(self, state, grasp_pos):
        """Park above the box's negative-X/Y sides before lowering the arm."""
        if "box_local_bounds" in state:
            lower, upper = state["box_local_bounds"]
            corners = np.array(list(product(*zip(lower, upper))))
            world = rotation(state["box_orientations"]).apply(corners) + state["box_positions"]
            box_lower = world[:, :2].min(0)
        else:
            box_lower = state["box_positions"][:2] - [.16, .12]
        xy = np.minimum(grasp_pos[:2] - [.05, .08], box_lower - self.box_staging_distance)
        return np.r_[xy, state["eef_pos"][2]]


def limited(vector: np.ndarray, maximum: float) -> np.ndarray:
    return vector * min(1.0, maximum / max(float(np.linalg.norm(vector)), 1e-12))


def downward_grasp_rotation(reference: Rotation, current: Rotation) -> Rotation:
    """Point the gripper +Z down, preserving its grasp yaw up to finger symmetry."""
    x = reference.as_matrix()[:, 0].copy()
    x[2] = 0.0
    if np.linalg.norm(x) < 1e-6:
        y = reference.as_matrix()[:, 1].copy()
        y[2] = 0.0
        x = np.cross(y, [0.0, 0.0, -1.0])
    x /= np.linalg.norm(x)
    z = np.array([0.0, 0.0, -1.0])
    aligned = Rotation.from_matrix(np.column_stack((x, np.cross(z, x), z)))
    symmetric = aligned * Rotation.from_rotvec([0.0, 0.0, math.pi])
    return min((aligned, symmetric), key=lambda candidate: (candidate * current.inv()).magnitude())


def horizontal_grasp_rotation(reference: Rotation, current: Rotation | None = None) -> Rotation:
    """Level an approach rotation with the shortest tilt correction."""
    z = reference.as_matrix()[:, 2]
    horizontal = np.array([z[0], z[1], 0.0])
    norm = float(np.linalg.norm(horizontal))
    if norm < 1e-8:
        raise ValueError("A vertical grasp cannot define a demonstrated horizontal approach direction")
    horizontal /= norm
    axis = np.cross(z, horizontal)
    sine = float(np.linalg.norm(axis))
    if sine < 1e-12:
        aligned = reference
    else:
        angle = math.atan2(sine, float(np.dot(z, horizontal)))
        aligned = Rotation.from_rotvec(axis * (angle / sine)) * reference
    if current is None:
        return aligned
    return closest_finger_symmetry(aligned, current)


def closest_finger_symmetry(aligned: Rotation, current: Rotation) -> Rotation:
    """Choose the equivalent finger roll without changing the approach axis."""
    symmetric = aligned * Rotation.from_rotvec([0.0, 0.0, math.pi])
    return min((aligned, symmetric), key=lambda candidate: (candidate * current.inv()).magnitude())


class UnreachableGraspError(ValueError):
    """The chosen grasp violates a necessary geometric arm-length bound."""


def wrist_reach_margin(pos, rot, shoulder_pos, wrist_to_tcp, arm_reach):
    """Necessary geometric reach check, independent of an IK solver's convergence."""
    wrist = pos - rot.apply(wrist_to_tcp)
    return float(arm_reach - np.linalg.norm(wrist - shoulder_pos))


def geometric_side_grasp(obs: dict, cfg: ControllerConfig, current: Rotation):
    """Grasp a truck end, with approach and finger closing directions horizontal."""
    truck = obs["toy_truck_positions"]
    truck_rot = rotation(obs["toy_truck_orientations"])
    if "truck_local_bounds" in obs:
        lower, upper = np.asarray(obs["truck_local_bounds"])
    else:
        lower = np.array([-0.07, -0.035, obs["truck_bottom_z"] - truck[2]])
        upper = np.array([0.07, 0.035, obs.get("truck_top_z", truck[2] + 0.035) - truck[2]])
    length_axis = int(np.argmax((upper - lower)[:2]))
    direction = truck_rot.as_matrix()[:, length_axis].copy()
    direction[2] = 0.0
    direction /= np.linalg.norm(direction)
    centre = (lower + upper) / 2
    half_length = float((upper[length_axis] - lower[length_axis]) / 2)
    contact = max(0.0, half_length - cfg.horizontal_grasp_inset)
    candidates = []
    reach_margins = []
    for sign in (-1.0, 1.0):
        offset = centre.copy()
        offset[length_axis] -= sign * contact
        offset[2] = lower[2] + cfg.horizontal_height_fraction * (upper[2] - lower[2])
        z = sign * direction
        y = np.cross([0.0, 0.0, 1.0], z)
        y /= np.linalg.norm(y)
        x = np.cross(y, z)
        rot = closest_finger_symmetry(Rotation.from_matrix(np.column_stack((x, y, z))), current)
        pos = truck + truck_rot.apply(offset)
        if "arm_reach" in obs:
            margin = wrist_reach_margin(pos, rot, obs["shoulder_pos"], obs["wrist_to_tcp"], obs["arm_reach"])
            reach_margins.append(margin)
            if margin < -0.003:
                continue
        score = (rot * current.inv()).magnitude() + 2.0 * np.linalg.norm(pos - obs["eef_pos"])
        candidates.append((score, offset, pos, rot))
    if not candidates:
        raise UnreachableGraspError(
            "horizontal 0-degree grasp outside arm reach: "
            f"best wrist distance {obs['arm_reach'] - max(reach_margins):.3f} m, "
            f"maximum arm reach {obs['arm_reach']:.3f} m"
        )
    _, offset, pos, rot = min(candidates, key=lambda item: item[0])
    return offset, pos, rot


class Toy2BoxController:
    """One-environment state machine. All poses are in the robot base frame."""

    def __init__(self, examples: list[GraspExample], cfg: ControllerConfig, manual_guidance: bool = False, motion=None,
                 strategy: str = "reference"):
        if strategy not in COLLECTION_STRATEGIES:
            raise ValueError(f"Unknown collection strategy: {strategy}")
        self.strategy = strategy
        self.examples = examples
        self.cfg = cfg
        self.phase = "settle"
        self.phase_time = 0.0
        self.elapsed = 0.0
        self.failure = None
        self.failure_kind = None
        self.lifted = False
        self.reference = None
        self.target_pos = None
        self.target_rot = None
        self.best_error = math.inf
        self.stall_time = 0.0
        self.transport_z = None
        self.aligned_time = 0.0
        self.manual_guidance = manual_guidance
        self.manual_gripper_closed = False
        self.manual_release_commanded = False
        self.motion = motion
        self.last_gripper_command = 1.0
        self.horizontal_offset = None

    @property
    def is_staged(self):
        return self.strategy in STAGED_STRATEGIES

    @property
    def is_horizontal(self):
        return self.strategy in HORIZONTAL_STRATEGIES

    @property
    def grasp_offset(self):
        return self.horizontal_offset if self.is_horizontal else self.reference.offset

    def enter(self, phase: str):
        self.phase = phase
        self.phase_time = 0.0
        self.best_error = math.inf
        self.stall_time = 0.0

    def fail(self, reason: str, kind: str | None = None):
        if self.failure is None:
            self.failure = reason
            self.failure_kind = kind

    @property
    def released(self) -> bool:
        return self.phase in ("release", "retreat", "wait") and (
            not self.manual_guidance or self.manual_release_commanded
        )

    def begin_release(self, ee: np.ndarray, ee_rot: Rotation):
        # Hold the current attainable pose while opening, rather than continuing
        # to push toward a target blocked by the box or the RMPFlow controller.
        self.target_pos, self.target_rot = ee.copy(), ee_rot
        self.enter("release")

    def choose_grasp(self, obs: dict):
        truck_rot = rotation(obs["toy_truck_orientations"])
        ee_rot = rotation(obs["eef_quat"])
        self.initial_truck_z = float(obs["toy_truck_positions"][2])
        if self.is_horizontal:
            try:
                self.horizontal_offset, self.grasp_pos, self.grasp_rot = geometric_side_grasp(obs, self.cfg, ee_rot)
            except UnreachableGraspError as error:
                self.fail(str(error), kind="unreachable_grasp")
            self.reference = None
            return
        choices = []
        for example in self.examples:
            pos = obs["toy_truck_positions"] + truck_rot.apply(example.offset)
            rot = truck_rot * example.orientation
            original_tilt = math.acos(float(np.clip(-rot.as_matrix()[2, 2], -1.0, 1.0)))
            if self.strategy in DOWNWARD_STRATEGIES:
                rot = downward_grasp_rotation(rot, ee_rot)
                if "eef_local_bounds" in obs:
                    from toy2box_box_clearance import obb_separation
                    lower, upper = obs["eef_local_bounds"]
                    hand = np.array(list(product(*zip(lower, upper))))
                    lower, upper = obs["box_local_bounds"]
                    box_points = np.array(list(product(*zip(lower, upper))))
                    box_rot = rotation(obs["box_orientations"]).as_matrix()
                    box_points = box_points @ box_rot.T + obs["box_positions"]
                    candidates = [rot, rot * Rotation.from_rotvec([0, 0, math.pi])]
                    gaps = [obb_separation(
                        candidate.apply(hand) + pos, candidate.as_matrix(), box_points, box_rot
                    ) for candidate in candidates]
                    # Preserve the nearer wrist roll when its housing already
                    # clears the box; unnecessarily flipping it can swing the
                    # forearm toward the box even if the hand itself moves away.
                    if gaps[0] < .04:
                        rot = candidates[int(np.argmax(gaps))]
            score = (rot * ee_rot.inv()).magnitude() + 2.0 * np.linalg.norm(pos - obs["eef_pos"])
            if self.strategy in DOWNWARD_STRATEGIES:
                # A sideways grasp's measured TCP offset is not valid after
                # flattening its orientation. Prefer truly top-down examples.
                score = (original_tilt, score)
            choices.append((score, example, pos, rot))
        if not choices:
            self.fail("reference dataset contains no successful grasp")
            return
        _, self.reference, self.grasp_pos, self.grasp_rot = min(choices, key=lambda item: item[0])
        self.initial_truck_z = float(obs["toy_truck_positions"][2])

    def project_errors(self, position_error, rotation_error):
        """Separate motion goals; stabilize XY during top-down rotation/descent."""
        pos, rot = position_error.copy(), rotation_error.copy()
        if self.strategy == "vertical_descend_first":
            if self.phase == "pre_descend":
                rot[:] = 0.0
                return pos, rot
            if self.phase in ("orient", "approach_xy"):
                return pos, rot
        if self.strategy == "vertical_xy_first" and self.phase in ("orient", "descend"):
            # Hold the already attained XY coordinates while rotating/lowering.
            # Without feedback, RMPflow can drift by >20 cm during rotation,
            # so a later Z-only command would close the gripper beside the toy.
            return pos, rot
        if self.is_horizontal or self.strategy in ("vertical_descend_first", "vertical_xy_first"):
            # Rotation-only commands let the arm change its elbow posture.
            # Holding the TCP pivot as a second objective can trap RMPflow at
            # its joint limits before the requested side-grasp pose is reached.
            if self.phase == "pre_descend":
                pos[:2], rot[:] = 0.0, 0.0
            elif self.phase in ("clear_box", "pre_xy", "approach_xy", "transfer"):
                pos[2], rot[:] = 0.0, 0.0
            elif self.phase == "orient":
                pos[:] = 0.0
            elif self.phase in ("descend", "lift"):
                pos[:2], rot[:] = 0.0, 0.0
            else:
                pos[:], rot[:] = 0.0, 0.0
            return pos, rot
        if self.strategy != "vertical_first":
            return pos, rot
        if self.phase == "orient":
            pos[:] = 0.0
        elif self.phase in ("approach_xy", "transfer"):
            pos[2], rot[:] = 0.0, 0.0
        elif self.phase in ("safe_raise", "descend", "lift"):
            pos[:2], rot[:] = 0.0, 0.0
        else:
            pos[:], rot[:] = 0.0, 0.0
        return pos, rot

    def action(self, obs: dict, dt: float, gripper_closed: bool | None = None) -> np.ndarray:
        """Update the phase from current observations, then emit one relative action."""
        self.elapsed += dt
        self.phase_time += dt
        if gripper_closed is not None:
            self.manual_gripper_closed = gripper_closed
        if self.manual_guidance:
            if self.phase == "close" and not self.manual_gripper_closed:
                self.phase_time = 0.0
            if self.phase == "release":
                if self.manual_gripper_closed:
                    self.phase_time = 0.0
                else:
                    self.manual_release_commanded = True
        if not all(np.isfinite(obs[key]).all() for key in POSE_KEYS):
            self.fail("non-finite observation")
            return np.zeros(7, dtype=np.float32)
        ee = obs["eef_pos"]
        ee_rot = rotation(obs["eef_quat"])
        truck = obs["toy_truck_positions"]
        box = obs["box_positions"]
        cfg = self.cfg
        inside_opening = obs["opening_margin"] >= 0.0
        inside_box_column = inside_opening and obs["truck_bottom_z"] >= obs["box_bottom_z"] - cfg.position_tolerance
        if self.target_pos is None:
            self.target_pos, self.target_rot = ee.copy(), ee_rot
        if not self.manual_guidance and self.elapsed > cfg.episode_timeout:
            self.fail(f"timeout in {self.phase}")
        elif not self.manual_guidance and self.phase_time > cfg.phase_timeout:
            if self.phase in ("transfer", "lower") and inside_box_column and self.strategy == "reference":
                self.begin_release(ee, ee_rot)
            else:
                self.fail(f"timeout in {self.phase}")
        if self.failure:
            return np.zeros(7, dtype=np.float32)
        if self.phase in ("transfer", "lower") and np.linalg.norm(ee - truck - self.held_offset) > 0.08:
            if inside_box_column:
                self.begin_release(ee, ee_rot)
            else:
                self.fail("truck slipped from the gripper")
                return np.zeros(7, dtype=np.float32)

        if self.motion is not None and self.motion.hold_requested(self.phase, dt):
            # Intentional pauses are recorded, but must not consume the phase's
            # progress watchdog. Grip state is preserved while holding still.
            self.phase_time = max(0.0, self.phase_time - dt)
            return np.array([0, 0, 0, 0, 0, 0, self.last_gripper_command], dtype=np.float32)
        phase_before_update = self.phase

        if self.phase == "settle":
            if self.phase_time >= cfg.settle_seconds:
                self.choose_grasp(obs)
                if self.failure:
                    return np.zeros(7, dtype=np.float32)
                if self.strategy == "vertical_first":
                    self.target_pos, self.target_rot = ee.copy(), self.grasp_rot
                    self.enter("orient")
                elif self.strategy == "vertical_descend_first":
                    self.target_pos = cfg.clearance_staging(obs, self.grasp_pos)
                    self.target_rot = ee_rot
                    self.enter("clear_box")
                elif self.strategy in DESCEND_FIRST_STRATEGIES:
                    self.target_pos, self.target_rot = ee.copy(), ee_rot
                    self.target_pos[2] = self.grasp_pos[2]
                    self.enter("pre_descend")
                elif self.strategy in XY_FIRST_STRATEGIES:
                    self.target_pos, self.target_rot = ee.copy(), ee_rot
                    self.target_pos[:2] = self.grasp_pos[:2]
                    self.enter("pre_xy")
                else:
                    self.enter("approach")
        elif self.phase == "clear_box":
            if self.reached(ee, ee_rot):
                self.target_pos = ee.copy()
                self.target_pos[2] = self.grasp_pos[2]
                self.enter("pre_descend")
        elif self.phase == "pre_descend":
            if self.reached(ee, ee_rot):
                if self.strategy != "vertical_descend_first":
                    self.grasp_rot = closest_finger_symmetry(self.grasp_rot, ee_rot)
                self.target_pos = ee.copy()
                self.target_rot = self.grasp_rot
                self.enter("orient")
        elif self.phase == "pre_xy":
            self.grasp_pos = truck + rotation(obs["toy_truck_orientations"]).apply(self.grasp_offset)
            self.target_pos[:2] = self.grasp_pos[:2]
            if ee[2] < self.grasp_pos[2] + cfg.approach_height - cfg.position_tolerance:
                self.fail("insufficient height before grasp rotation")
            elif self.reached(ee, ee_rot):
                self.grasp_rot = closest_finger_symmetry(
                    self.grasp_rot, ee_rot
                )
                self.target_pos = ee.copy()
                if self.strategy == "vertical_xy_first":
                    self.target_pos[:2] = self.grasp_pos[:2]
                self.target_rot = self.grasp_rot
                self.enter("orient")
        elif self.phase == "orient":
            aligned = self.reached(ee, ee_rot) if self.is_horizontal or self.strategy in ("vertical_xy_first", "vertical_descend_first") else (
                (self.target_rot * ee_rot.inv()).magnitude() < min(cfg.rotation_tolerance, 0.08)
            )
            if aligned and self.strategy in DESCEND_FIRST_STRATEGIES:
                self.target_pos[:2] = self.grasp_pos[:2]
                self.enter("approach_xy")
            elif aligned and self.strategy in XY_FIRST_STRATEGIES:
                self.target_pos[2] = self.grasp_pos[2]
                self.enter("descend")
            elif aligned:
                self.target_pos = ee.copy()
                safe_z = self.grasp_pos[2] + cfg.approach_height
                if ee[2] < safe_z - cfg.position_tolerance:
                    self.target_pos[2] = safe_z
                    self.enter("safe_raise")
                else:
                    self.target_pos[:2] = self.grasp_pos[:2]
                    self.enter("approach_xy")
        elif self.phase == "safe_raise":
            if self.reached(ee, ee_rot):
                self.target_pos = np.array([self.grasp_pos[0], self.grasp_pos[1], ee[2]])
                self.enter("approach_xy")
        elif self.phase == "approach_xy":
            self.grasp_pos = truck + rotation(obs["toy_truck_orientations"]).apply(self.grasp_offset)
            self.target_pos[:2] = self.grasp_pos[:2]
            if self.strategy in DESCEND_FIRST_STRATEGIES:
                if self.reached(ee, ee_rot):
                    if self.is_horizontal and (self.grasp_rot * ee_rot.inv()).magnitude() > min(cfg.rotation_tolerance, cfg.horizontal_rotation_tolerance):
                        self.fail("horizontal grasp orientation lost during XY travel")
                    elif self.is_horizontal and abs(ee[2] - self.grasp_pos[2]) > cfg.position_tolerance:
                        self.fail("horizontal grasp height lost during rotation or XY travel")
                    else:
                        self.target_pos = ee.copy()
                        self.enter("close")
            elif ee[2] < self.grasp_pos[2] + cfg.approach_height - cfg.position_tolerance:
                self.fail("insufficient height during XY approach")
            elif self.reached(ee, ee_rot):
                self.target_pos = np.array([ee[0], ee[1], self.grasp_pos[2]])
                self.enter("descend")
        elif self.phase == "approach":
            self.target_pos = self.grasp_pos + np.array([0.0, 0.0, cfg.approach_height])
            self.target_rot = self.grasp_rot
            if self.reached(ee, ee_rot):
                self.enter("descend")
        elif self.phase == "descend":
            truck_rot = rotation(obs["toy_truck_orientations"])
            if self.is_staged:
                live_grasp = truck + truck_rot.apply(self.grasp_offset)
                if np.linalg.norm(live_grasp[:2] - self.target_pos[:2]) > 0.035:
                    self.fail("truck moved sideways during vertical descent")
                self.target_pos[2] = live_grasp[2]
            else:
                # Follow object motion in the original combined-axis strategy.
                self.target_pos = truck + truck_rot.apply(self.reference.offset)
                self.target_rot = truck_rot * self.reference.orientation
            if not self.failure and self.reached(ee, ee_rot):
                if self.is_horizontal and (self.grasp_rot * ee_rot.inv()).magnitude() > min(cfg.rotation_tolerance, cfg.horizontal_rotation_tolerance):
                    self.fail("horizontal grasp orientation lost during vertical descent")
                elif self.is_horizontal and np.linalg.norm(ee[:2] - live_grasp[:2]) > cfg.position_tolerance:
                    self.fail("horizontal grasp XY alignment lost during rotation or descent")
                elif self.strategy in DOWNWARD_STRATEGIES:
                    self.target_pos = ee.copy()
                if not self.failure:
                    self.enter("close")
        elif self.phase == "close":
            if self.phase_time >= cfg.grip_seconds:
                self.held_offset = ee - truck
                self.lift_start_truck_z = float(truck[2])
                # Clear the box rim with the *bottom* of the truck before any
                # horizontal motion. A fixed EE displacement does not ensure this.
                self.transport_z = max(
                    truck[2] + cfg.lift_height,
                    truck[2] + obs["box_top_z"] + cfg.transport_clearance - obs["truck_bottom_z"]
                    + (cfg.transfer_height_reserve if self.is_staged else 0.0),
                )
                self.target_pos = ee.copy()
                self.target_pos[2] = self.transport_z + self.held_offset[2]
                self.enter("lift")
        elif self.phase == "lift":
            required_bottom = obs["box_top_z"] + cfg.transport_clearance + (
                cfg.transfer_height_reserve if self.is_staged else 0.0
            )
            clearance_ok = obs["truck_bottom_z"] >= required_bottom
            if not clearance_ok:
                # Compensate for grasp settling without moving sideways.
                self.target_pos[2] = max(
                    self.target_pos[2], ee[2] + required_bottom - obs["truck_bottom_z"] + 0.005
                )
            minimum_lift = truck[2] - self.lift_start_truck_z >= cfg.lift_height - cfg.position_tolerance
            if clearance_ok and minimum_lift:
                if truck[2] - self.lift_start_truck_z < 0.06:
                    self.fail("truck did not lift with the gripper")
                else:
                    self.lifted = True
                    self.held_offset = ee - truck
                    desired_truck = np.array([box[0], box[1], truck[2]])
                    self.target_pos = desired_truck + self.held_offset
                    self.enter("transfer")
            elif ee[2] - (self.lift_start_truck_z + self.held_offset[2]) >= 0.06:
                if truck[2] - self.lift_start_truck_z < 0.03:
                    self.fail("truck did not lift with the gripper")
        elif self.phase == "transfer":
            aligned = inside_opening and (
                not self.is_staged
                or np.linalg.norm(self.target_pos[:2] - ee[:2]) < cfg.position_tolerance
            )
            self.aligned_time = self.aligned_time + dt if aligned else 0.0
            if obs["truck_bottom_z"] < obs["box_top_z"] + cfg.transport_clearance - cfg.position_tolerance:
                # Recover clearance vertically before resuming the transfer.
                self.target_pos = ee.copy()
                self.target_pos[2] += obs["box_top_z"] + cfg.transport_clearance - obs["truck_bottom_z"] + 0.005
                self.enter("lift")
            elif self.aligned_time >= cfg.alignment_seconds:
                if self.is_staged:
                    self.begin_release(ee, ee_rot)
                else:
                    # Position the truck just ABOVE the rim, not inside the box
                    # while it is still held. The latter can block the gripper.
                    self.target_pos = ee.copy()
                    self.target_pos[2] += obs["box_top_z"] + cfg.release_clearance - obs["truck_bottom_z"]
                    self.target_rot = ee_rot
                    self.enter("lower")
        elif self.phase == "lower":
            if not inside_opening:
                self.fail("truck moved outside the box opening before release")
            elif obs["truck_bottom_z"] <= obs["box_top_z"] + cfg.release_clearance + cfg.position_tolerance:
                self.begin_release(ee, ee_rot)
        elif self.phase == "release":
            if self.phase_time >= cfg.release_seconds:
                if self.is_staged:
                    self.target_pos = ee.copy()
                    self.enter("wait")
                else:
                    self.target_pos = ee + np.array([0.0, 0.0, 0.10])
                    self.enter("retreat")
        elif self.phase == "retreat":
            if self.reached(ee, ee_rot):
                self.enter("wait")

        pos_error = self.target_pos - ee
        rot_error = (self.target_rot * ee_rot.inv()).as_rotvec()
        pos_error, rot_error = self.project_errors(pos_error, rot_error)
        if not self.manual_guidance and self.phase in (
            "orient", "clear_box", "pre_descend", "pre_xy", "safe_raise", "approach_xy", "approach", "descend",
            "lift", "transfer", "lower", "retreat"
        ):
            error = float(np.linalg.norm(pos_error) + 0.05 * np.linalg.norm(rot_error))
            if error < self.best_error - 0.002:
                self.best_error, self.stall_time = error, 0.0
            else:
                self.stall_time += dt
            if not self.reached(ee, ee_rot) and self.stall_time >= cfg.stall_seconds:
                if self.phase in ("transfer", "lower") and inside_box_column and self.strategy == "reference":
                    self.begin_release(ee, ee_rot)
                    pos_error, rot_error = np.zeros(3), np.zeros(3)
                else:
                    self.fail(f"stalled in {self.phase}")
        close = self.phase in ("close", "lift", "transfer", "lower")
        command = np.r_[
            limited(cfg.gain * pos_error, cfg.max_translation),
            limited(cfg.gain * rot_error, cfg.max_rotation),
        ]
        if (
            self.motion is not None and self.phase == phase_before_update
            and not (self.is_staged and self.phase == "orient")
        ):
            command = self.motion.modify(self.phase, pos_error, rot_error, cfg, dt)
        command[:3], command[3:] = self.project_errors(command[:3], command[3:])
        self.last_gripper_command = -1.0 if close else 1.0
        return np.r_[command, self.last_gripper_command].astype(np.float32)

    def reached(self, ee: np.ndarray, ee_rot: Rotation) -> bool:
        pos_error, rot_error = self.project_errors(
            self.target_pos - ee, (self.target_rot * ee_rot.inv()).as_rotvec()
        )
        if self.is_horizontal and self.phase == "orient":
            # This stage sends rotation commands only.
            pos_error[:] = 0.0
        return (
            np.linalg.norm(pos_error) < (self.cfg.horizontal_position_tolerance
                                        if self.is_horizontal and self.phase in ("pre_descend", "descend", "approach_xy")
                                        else self.cfg.position_tolerance)
            and np.linalg.norm(rot_error) < (
                min(self.cfg.rotation_tolerance, self.cfg.horizontal_rotation_tolerance)
                if self.is_horizontal and self.phase == "orient" else
                min(self.cfg.rotation_tolerance, 0.08) if self.phase == "orient" else self.cfg.rotation_tolerance
            )
        )


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", default=TASK, choices=[TASK])
    # AppLauncher probes parse_known_args before restoring --help, so validate
    # this required value after final parsing to keep bare --help usable.
    parser.add_argument("--reference_dataset", type=Path, help="Required: successful keyboard demonstration dataset.")
    parser.add_argument("--dataset_file", type=Path, default=Path("datasets/toy2box_agibot_auto.hdf5"))
    parser.add_argument("--num_demos", type=int, default=20)
    parser.add_argument("--max_attempts", type=int, default=1000)
    parser.add_argument("--exit_on_finish", action="store_true",
                        help="Close the GUI immediately after collection ends. Headless runs always exit.")
    parser.add_argument("--num_success_steps", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--inspect_reference", action="store_true", help="Inspect grasps without launching Isaac Sim.")
    parser.add_argument(
        "--collection_strategy", choices=COLLECTION_STRATEGIES, default="vertical_first",
        help="vertical_first (rotate/XY/Z); vertical_descend_first (clear box/Z/rotate/XY); vertical_xy_first (XY/rotate/Z).",
    )
    parser.add_argument(
        "--motion_style", choices=("standard", "varied"), default=None,
        help="Defaults to varied for staged collection, standard for manual/reference. Varied adds speed changes/pauses.",
    )
    parser.add_argument("--motion_variation_strength", type=float, default=1.0, help="Variation strength from 0 to 1.")
    parser.add_argument(
        "--target_idle_fraction", type=float, default=0.21,
        help="Approximate total idle fraction in varied mode, scaled by strength; 0 keeps brief random pauses only.",
    )
    parser.add_argument(
        "--manual_guidance", action="store_true",
        help="Show recommended keys; move the robot only using the human keyboard input (GUI required).",
    )
    parser.add_argument(
        "--full_sequence", action="store_true",
        help="Manual control with top/left views and the full sequence displayed at once.",
    )
    parser.add_argument("--multi_view", action="store_true", help="Show top and robot-left operator viewports.")
    parser.add_argument(
        "--sequence_order", choices=("rotation_xy_z", "xy_rotation_z"), default="rotation_xy_z",
        help="Reference strategy only: grasp preparation order after first raising to a safe height.",
    )
    parser.add_argument("--hint_interval", type=float, default=0.1, help="Minimum seconds between key hint updates.")
    parser.add_argument("--keyboard_pos_step", type=float, default=0.005, help="Manual position increment in meters.")
    parser.add_argument("--keyboard_rot_step", type=float, default=0.025, help="Manual Euler increment in radians.")
    parser.add_argument("--guide_batch_size", type=int, default=5, help="Maximum presses in one guidance batch.")
    parser.add_argument(
        "--tap_settle_seconds", type=float, default=0.25, help="Response time allowed per discrete tap."
    )
    config_help = {
        "horizontal_height_fraction": "Side-grasp TCP height within the truck bounds (0 to 1).",
        "horizontal_grasp_inset": "TCP insertion from a truck end, in meters.",
        "horizontal_rotation_tolerance": "Numerical rotation error allowed around the exact zero-tilt goal, in radians.",
    }
    for name, field in ControllerConfig.__dataclass_fields__.items():
        parser.add_argument(f"--{name}", type=float, default=field.default, help=config_help.get(name))
    return parser


def resolve_motion_style(args):
    if args.motion_style is None:
        args.motion_style = (
            "varied" if args.collection_strategy in STAGED_STRATEGIES and not args.manual_guidance else "standard"
        )


def validate_args(args):
    if args.full_sequence:
        args.manual_guidance = True
        args.multi_view = True
    resolve_motion_style(args)
    if args.manual_guidance and args.headless:
        raise ValueError("--manual_guidance requires a GUI; remove --headless")
    if args.multi_view and args.headless:
        raise ValueError("--multi_view requires a GUI; remove --headless")
    if args.motion_style == "varied" and args.manual_guidance:
        raise ValueError("--motion_style varied is for automatic collection; omit manual guidance flags")
    if not math.isfinite(args.motion_variation_strength) or not 0 <= args.motion_variation_strength <= 1:
        raise ValueError("motion_variation_strength must be finite and between 0 and 1")
    if not math.isfinite(args.target_idle_fraction) or not 0 <= args.target_idle_fraction <= 0.5:
        raise ValueError("target_idle_fraction must be finite and between 0 and 0.5")
    if args.horizontal_height_fraction > 1.0:
        raise ValueError("horizontal_height_fraction must be at most 1")
    for name in ("hint_interval", "keyboard_pos_step", "keyboard_rot_step", "tap_settle_seconds"):
        if not math.isfinite(getattr(args, name)) or getattr(args, name) <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if args.guide_batch_size <= 0:
        raise ValueError("guide_batch_size must be positive")
    if min(args.num_demos, args.max_attempts, args.num_success_steps) <= 0:
        raise ValueError("num_demos, max_attempts, and num_success_steps must be positive")
    if args.max_attempts < args.num_demos:
        raise ValueError("max_attempts must be >= num_demos")
    for name in ControllerConfig.__dataclass_fields__:
        value = getattr(args, name)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if args.dataset_file.suffix != ".hdf5":
        raise ValueError("dataset_file must end in .hdf5")
    if args.dataset_file.resolve() == args.reference_dataset.resolve():
        raise ValueError("Output must differ from the reference dataset")
    if args.dataset_file.exists() or args.dataset_file.with_suffix(".run.json").exists():
        raise FileExistsError(f"Output already exists: {args.dataset_file} (or its .run.json log); choose a new name")


def collect(args, examples: list[GraspExample], simulation_app) -> int:
    resolve_motion_style(args)
    # Import simulator modules only after AppLauncher has started Isaac Sim.
    import gymnasium as gym
    import torch

    import isaaclab_tasks  # noqa: F401
    from isaaclab.devices import Se3Keyboard, Se3KeyboardCfg
    from isaaclab.envs.mdp.recorders.recorders_cfg import ActionStateRecorderManagerCfg
    from isaaclab.managers import DatasetExportMode
    from isaaclab_tasks.utils.parse_cfg import parse_env_cfg

    cfg = parse_env_cfg(args.task, device=args.device, num_envs=1)
    cfg.seed = args.seed
    cfg.env_name = args.task
    cfg.actions.arm_action.use_relative_mode = True
    cfg.actions.arm_action.scale = 1.0
    cfg.observations.policy.concatenate_terms = False
    cfg.observations.policy.enable_corruption = False
    box_avoidance_enabled = args.collection_strategy == "vertical_descend_first"
    if box_avoidance_enabled:
        from toy2box_box_clearance import configure_box_contact_sensor
        configure_box_contact_sensor(cfg)
    success_term = cfg.terminations.success
    # Own all resets so an automatic reset cannot erase the episode before export.
    cfg.terminations.success = None
    cfg.terminations.time_out = None
    drop_term = cfg.terminations.toy_truck_dropping
    cfg.terminations.toy_truck_dropping = None
    cfg.recorders = ActionStateRecorderManagerCfg()
    cfg.recorders.dataset_export_dir_path = str(args.dataset_file.resolve().parent)
    cfg.recorders.dataset_filename = args.dataset_file.stem
    cfg.recorders.dataset_export_mode = DatasetExportMode.EXPORT_SUCCEEDED_ONLY
    cfg.recorders.export_in_record_pre_reset = False
    controller_cfg = ControllerConfig(**{key: getattr(args, key) for key in ControllerConfig.__dataclass_fields__})
    report = {
        "task": args.task,
        "seed": args.seed,
        "reference_dataset": str(args.reference_dataset.resolve()),
        "dataset_file": str(args.dataset_file.resolve()),
        "controller": asdict(controller_cfg),
        "collection_strategy": args.collection_strategy,
        "grasp_mode": ("horizontal" if args.collection_strategy in HORIZONTAL_STRATEGIES else
                       "downward" if args.collection_strategy in DOWNWARD_STRATEGIES else "reference"),
        "grasp_planner": ("object_geometry" if args.collection_strategy in HORIZONTAL_STRATEGIES else "reference"),
        "side_approach_tilt_degrees": 0.0 if args.collection_strategy in HORIZONTAL_STRATEGIES else None,
        "attempts": [],
        "successful_demos": 0,
        "stop_reason": None,
        "mode": (
            "manual_sequence" if args.full_sequence else ("manual_guidance" if args.manual_guidance else "automatic")
        ),
        "sequence_order": args.sequence_order if args.full_sequence else None,
        "motion_style": args.motion_style,
        "motion_variation_strength": args.motion_variation_strength if args.motion_style == "varied" else 0.0,
        "target_idle_fraction": args.target_idle_fraction if args.motion_style == "varied" else None,
        "operator_views": ["top", "robot_left"] if args.multi_view else [],
        "manual_input": {
            "type": "tap_counts", "position_step": args.keyboard_pos_step,
            "rotation_step": args.keyboard_rot_step, "batch_size": args.guide_batch_size,
        } if args.manual_guidance else None,
    }
    report_path = args.dataset_file.with_suffix(".run.json")
    env = gym.make(args.task, cfg=cfg).unwrapped
    reach_robot = env.scene["robot"] if args.collection_strategy in HORIZONTAL_STRATEGIES else None
    reach_body_ids = ([reach_robot.body_names.index(name) for name in
                       ("Link1_r", "Link3_r", "Link5_r", "Link7_r", "right_base_link", "right_gripper_center")]
                      if reach_robot is not None else None)
    keyboard = None
    guide = None
    views = None
    box_guard = None
    controls = {"reset": False, "paused": False, "next_row": False}

    def request_reset():
        controls["reset"] = True

    def toggle_pause():
        controls["paused"] = not controls["paused"]
        print(f"[AUTO] Paused: {controls['paused']}")

    def next_sequence_row():
        controls["next_row"] = True

    def snapshot(observation):
        state = {key: observation["policy"][key][0].detach().cpu().numpy().copy() for key in POSE_KEYS}
        state["box_bottom_z"], state["box_top_z"] = height_limits(
            box_corners, state["box_positions"], state["box_orientations"]
        )
        state["truck_bottom_z"], state["truck_top_z"] = height_limits(
            truck_corners, state["toy_truck_positions"], state["toy_truck_orientations"]
        )
        state["truck_local_bounds"] = np.array([truck_corners.min(axis=0), truck_corners.max(axis=0)])
        state["box_local_bounds"] = np.array([box_corners.min(axis=0), box_corners.max(axis=0)])
        state["opening_margin"] = opening_margin(box_corners, truck_corners, state, args.opening_inset)
        if reach_robot is not None:
            points = reach_robot.data.body_pos_w[0, reach_body_ids].detach().cpu().numpy()
            root_pos = reach_robot.data.root_pos_w[0].detach().cpu().numpy()
            root_rot = rotation(reach_robot.data.root_quat_w[0].detach().cpu().numpy())
            tcp_rot = rotation(reach_robot.data.body_quat_w[0, reach_body_ids[-1]].detach().cpu().numpy())
            state["shoulder_pos"] = root_rot.inv().apply(points[0] - root_pos)
            state["arm_reach"] = float(np.linalg.norm(np.diff(points[:4], axis=0), axis=1).sum())
            state["wrist_to_tcp"] = tcp_rot.inv().apply(points[5] - points[4])
        if box_guard is not None:
            state["eef_local_bounds"] = box_guard.gripper_bounds_in_tcp()
        return state

    try:
        if args.motion_style == "varied":
            from toy2box_motion_variation import MotionVariation, MotionVariationConfig
        if args.full_sequence or args.multi_view:
            from toy2box_manual_sequence import (
                FullSequenceDisplay, ManualSequenceSession, ManualViewports, build_sequence,
            )
        if env.action_manager.total_action_dim != 7:
            raise RuntimeError("Expected six arm delta actions plus one gripper action")
        box_corners = read_local_bounds(env, "box")
        truck_corners = read_local_bounds(env, "toy_truck")
        if box_avoidance_enabled:
            from toy2box_box_clearance import BoxClearanceGuard
            box_guard = BoxClearanceGuard(env, box_corners)
        if not args.headless:
            keyboard_cfg = Se3KeyboardCfg(
                pos_sensitivity=args.keyboard_pos_step,
                rot_sensitivity=args.keyboard_rot_step,
                sim_device=env.device,
            )
            if args.manual_guidance:
                keyboard = create_tap_keyboard(Se3Keyboard, keyboard_cfg)
            else:
                keyboard = Se3Keyboard(keyboard_cfg)
            keyboard.add_callback("R", request_reset)
            keyboard.add_callback("P", toggle_pause)
            if args.full_sequence:
                keyboard.add_callback("N", next_sequence_row)
        if args.manual_guidance:
            guide = FullSequenceDisplay() if args.full_sequence else KeyboardGuideDisplay(args.hint_interval)
            print(
                f"[GUIDE] Counted taps: one press = {args.keyboard_pos_step * 1000:g} mm / "
                f"{math.degrees(args.keyboard_rot_step):.2f} deg. Tap and release for each count."
            )
        if args.multi_view:
            views = ManualViewports()
        print("[AUTO] R: discard/reset, P: pause/resume, Ctrl+C: finish")
        with torch.inference_mode():
            observation = reset_recording_instance(env)
            for attempt in range(1, args.max_attempts + 1):
                if (
                    not simulation_app.is_running() or env.sim.is_stopped()
                    or report["successful_demos"] >= args.num_demos
                ):
                    break
                controls["reset"] = False
                controls["next_row"] = False
                motion = None
                if box_guard is not None:
                    box_guard.reset_stats()
                if args.full_sequence:
                    # Settle objects before computing the one-time full plan.
                    idle = torch.zeros((1, 7), device=env.device)
                    idle[:, 6] = 1.0
                    for _ in range(math.ceil(controller_cfg.settle_seconds / env.step_dt)):
                        observation, *_ = env.step(idle)
                if views is not None:
                    views.recenter(env)
                if args.manual_guidance:
                    keyboard.reset()
                    if args.full_sequence:
                        state = snapshot(observation)
                        calibration = Toy2BoxController(examples, controller_cfg, strategy=args.collection_strategy)
                        calibration.choose_grasp(state)
                        steps, transport_z = build_sequence(
                            state, calibration.grasp_pos, calibration.grasp_rot, controller_cfg,
                            args.keyboard_pos_step, args.keyboard_rot_step, args.sequence_order,
                            args.collection_strategy,
                        )
                        controller = ManualSequenceSession(steps, state, calibration.reference, transport_z)
                        guide.update(controller.phase, controller.text())
                    else:
                        controller = Toy2BoxController(
                            examples, controller_cfg, manual_guidance=True, strategy=args.collection_strategy
                        )
                    tap_control = TapMotionController(
                        args.keyboard_pos_step, args.keyboard_rot_step, args.tap_settle_seconds
                    )
                    counted_guide = CountedKeyGuide(
                        args.keyboard_pos_step, args.keyboard_rot_step, args.guide_batch_size
                    )
                else:
                    if args.motion_style == "varied" and args.motion_variation_strength > 0:
                        motion = MotionVariation(
                            args.seed + attempt - 1,
                            MotionVariationConfig(
                                strength=args.motion_variation_strength,
                                target_idle_fraction=args.target_idle_fraction,
                                idle_tail_seconds=(
                                    max(controller_cfg.release_seconds, args.num_success_steps * env.step_dt)
                                    if args.collection_strategy in STAGED_STRATEGIES else env.step_dt
                                ),
                                position_offset=0.0 if args.collection_strategy in STAGED_STRATEGIES else 0.008,
                                rotation_offset=0.0 if args.collection_strategy in STAGED_STRATEGIES else 0.025,
                            ),
                        )
                        controller = Toy2BoxController(
                            examples, controller_cfg, motion=motion, strategy=args.collection_strategy
                        )
                    else:
                        controller = Toy2BoxController(examples, controller_cfg, strategy=args.collection_strategy)
                next_step_time = time.monotonic()
                consecutive_success = 0
                success = False
                last_phase = None
                phase_trace = []
                reason = "simulation stopped"
                while simulation_app.is_running():
                    if box_guard is not None:
                        violation = box_guard.check()
                        if violation:
                            reason = violation
                            break
                    if controls["reset"]:
                        reason = "manual reset"
                        break
                    if controls["paused"] or not env.sim.is_playing():
                        env.sim.render()
                        if env.sim.is_stopped():
                            break
                        continue
                    if args.manual_guidance:
                        state = snapshot(observation)
                        presses = keyboard.pop_presses()
                        # Only physical key-down edges add to this servo's pose goal.
                        human_action = tap_control.action(state, presses, env.step_dt)
                        previous_phase = controller.phase
                        action = controller.action(state, env.step_dt, tap_control.closed)
                        if args.full_sequence:
                            if controls["next_row"]:
                                controller.advance()
                                controls["next_row"] = False
                            hint = controller.text()
                        elif controller.phase != previous_phase:
                            # Do not carry queued movements across a phase boundary.
                            tap_control.clear_motion(state)
                            human_action = tap_control.action(state, [], 0.0)
                        if not args.full_sequence:
                            hint = counted_guide.update(controller, state, action, tap_control, presses)
                        guide.update(controller.phase, hint)
                        applied_action = torch.as_tensor(human_action, device=env.device)
                    else:
                        action = controller.action(snapshot(observation), env.step_dt)
                        applied_action = torch.as_tensor(action, device=env.device)
                    if controller.phase != last_phase:
                        state = snapshot(observation)
                        phase_trace.append({
                            "phase": controller.phase, "seconds": round(controller.elapsed, 3),
                            "gripper_command": float(action[6]),
                            "applied_gripper_command": float(applied_action[6]),
                            "eef_pos": state["eef_pos"].tolist(),
                            "eef_quat": state["eef_quat"].tolist(),
                            "target_eef_pos": controller.target_pos.tolist() if controller.target_pos is not None else None,
                            "target_eef_quat": controller.target_rot.as_quat()[[3, 0, 1, 2]].tolist(),
                            "truck_pos": state["toy_truck_positions"].tolist(),
                            "box_pos": state["box_positions"].tolist(),
                            "opening_margin": state["opening_margin"],
                        })
                        print(f"[AUTO] Attempt {attempt}: {controller.phase}")
                        if controller.phase == "release":
                            if args.manual_guidance:
                                print("[GUIDE] Release stage reached: follow the K / OPEN instruction.")
                            else:
                                print(f"[AUTO] Gripper OPEN; opening margin={state['opening_margin']:.3f} m")
                        if controller.phase == "lift":
                            state = snapshot(observation)
                            print(
                                f"[AUTO] Box top z={state['box_top_z']:.3f}, "
                                f"truck bottom z={state['truck_bottom_z']:.3f}, "
                                f"target EE z={controller.target_pos[2]:.3f} (base frame)"
                            )
                        last_phase = controller.phase
                    if controller.failure:
                        reason = controller.failure
                        break
                    observation, _, terminated, truncated, _ = env.step(
                        applied_action.unsqueeze(0)
                    )
                    if motion is not None:
                        motion.observe_action(action, env.step_dt)
                    if box_guard is not None:
                        violation = box_guard.check()
                        if violation:
                            reason = violation
                            break
                    if args.manual_guidance:
                        next_step_time = max(next_step_time + env.step_dt, time.monotonic())
                        time.sleep(max(0.0, next_step_time - time.monotonic()))
                    if bool(terminated[0]) or bool(truncated[0]):
                        reason = "unexpected environment reset"
                        break
                    if bool(drop_term.func(env, **drop_term.params)[0]):
                        reason = "truck dropped below the table"
                        break
                    # Count success during release/retreat too; an unattainable
                    # retreat target must not discard an already placed truck.
                    task_success = bool(success_term.func(env, **success_term.params)[0])
                    valid = success_ready(controller, task_success)
                    consecutive_success = consecutive_success + 1 if valid else 0
                    if consecutive_success >= args.num_success_steps:
                        env.recorder_manager.record_pre_reset([0], force_export_or_skip=False)
                        env.recorder_manager.set_success_to_episodes(
                            [0], torch.tensor([[True]], dtype=torch.bool, device=env.device)
                        )
                        env.recorder_manager.export_episodes([0])
                        report["successful_demos"] = env.recorder_manager.exported_successful_episode_count
                        print(f"[AUTO] SUCCESS: {report['successful_demos']}/{args.num_demos} saved")
                        success, reason = True, "success"
                        break
                report["attempts"].append({
                    "attempt": attempt,
                    "success": success,
                    "reason": reason,
                    "failure_kind": getattr(controller, "failure_kind", None),
                    "phase": controller.phase,
                    "seconds": round(controller.elapsed, 3),
                    "reference_episode": controller.reference.episode if controller.reference else None,
                    "truck_target_z": float(controller.transport_z) if controller.transport_z is not None else None,
                    "target_eef_pos": controller.target_pos.tolist() if controller.target_pos is not None else None,
                    "final_eef_pos": snapshot(observation)["eef_pos"].tolist(),
                    "final_eef_quat": snapshot(observation)["eef_quat"].tolist(),
                    "target_eef_quat": (controller.target_rot.as_quat()[[3, 0, 1, 2]].tolist()
                                        if controller.target_rot is not None else None),
                    "final_truck_pos": snapshot(observation)["toy_truck_positions"].tolist(),
                    "final_box_pos": snapshot(observation)["box_positions"].tolist(),
                    "opening_margin": snapshot(observation)["opening_margin"],
                    "release_commanded": controller.released,
                    "task_success": bool(success_term.func(env, **success_term.params)[0]),
                    "phase_trace": phase_trace,
                    "full_sequence": controller.export_plan() if args.full_sequence else None,
                    "motion_variation": motion.export() if motion is not None else None,
                    "reset_completed": False,
                    "box_clearance": box_guard.export() if box_guard is not None else None,
                })
                report_path.write_text(json.dumps(report, indent=2) + "\n")
                print(f"[AUTO] {reason}; saved {report['successful_demos']}/{args.num_demos}", flush=True)
                # Also reset after the final success or exhausted attempt budget.
                if simulation_app.is_running() and not env.sim.is_stopped():
                    observation = reset_recording_instance(env)
                    report["attempts"][-1]["reset_completed"] = True
                    report_path.write_text(json.dumps(report, indent=2) + "\n")
                    print("[AUTO] Scene reset completed.", flush=True)
                if getattr(controller, "failure_kind", None) == "unreachable_grasp":
                    report["stop_reason"] = (
                        "Collection stopped: the horizontal 0-degree grasp target is outside arm reach. "
                        "Adjust the grasp position or work height before retrying."
                    )
                    report_path.write_text(json.dumps(report, indent=2) + "\n")
                    print(f"[AUTO] {report['stop_reason']}", flush=True)
                    break
            review_collection_result(
                env, simulation_app, report, report_path, args.num_demos,
                headless=args.headless, exit_on_finish=args.exit_on_finish,
            )
    except KeyboardInterrupt:
        print("[AUTO] Interrupted; completed demonstrations are preserved.")
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        # Drop keyboard before the application and its input service are closed.
        keyboard = None
        if guide is not None:
            guide.close()
        if views is not None:
            views.close()
        env.close()
    print(f"[AUTO] Saved {report['successful_demos']} demonstrations to {args.dataset_file}", flush=True)
    print(f"[AUTO] Attempt log: {report_path}", flush=True)
    return 0 if report["successful_demos"] >= args.num_demos else 2


def main() -> int:
    parser = create_parser()
    inspect_only = "--inspect_reference" in sys.argv
    if not inspect_only:
        from isaaclab.app import AppLauncher

        AppLauncher.add_app_launcher_args(parser)
    args = parser.parse_args()
    if args.reference_dataset is None:
        parser.error("--reference_dataset is required")
    examples = load_grasps(args.reference_dataset)
    print(f"[AUTO] Loaded {len(examples)} successful grasp examples from {args.reference_dataset}")
    if inspect_only:
        for example in examples:
            print(f"  {example.episode}: grasp step {example.step}, truck-frame offset {example.offset.round(4)}")
        return 0
    validate_args(args)
    args.dataset_file.resolve().parent.mkdir(parents=True, exist_ok=True)
    app = AppLauncher(args)
    try:
        return collect(args, examples, app.app)
    except Exception:
        # Kit shutdown can suppress an exception's pending stderr output.
        # Emit it before closing the application so startup failures are visible.
        import traceback
        traceback.print_exc()
        raise
    finally:
        app.app.close()


if __name__ == "__main__":
    sys.exit(main())
