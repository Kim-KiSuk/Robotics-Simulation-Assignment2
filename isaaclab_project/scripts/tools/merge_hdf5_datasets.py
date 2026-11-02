# Copyright (c) 2022-2025, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import h5py
import json
import os

parser = argparse.ArgumentParser(description="Merge a set of HDF5 datasets.")
parser.add_argument(
    "--input_files",
    type=str,
    nargs="+",
    required=True,
    help="A list of paths to HDF5 files to merge.",
)
parser.add_argument("--output_file", type=str, default="merged_dataset.hdf5", help="File path to merged output.")
parser.add_argument(
    "--task", type=str, default=None,
    help="Explicit task name for inputs missing env_name. A recorded conflicting task is still rejected.",
)

args_cli = parser.parse_args()


def merge_datasets():
    env_name = args_cli.task
    action_shape = None
    for filepath in args_cli.input_files:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"The dataset file {filepath} does not exist.")
        with h5py.File(filepath, "r") as source:
            name = json.loads(source["data"].attrs["env_args"]).get("env_name")
            if not name:
                if not args_cli.task:
                    raise ValueError(
                        f"Task name (env_args.env_name) is missing in {filepath}. "
                        "If this file belongs to the same task, specify it explicitly with --task."
                    )
                name = args_cli.task
            if env_name is None:
                env_name = name
            elif name != env_name:
                raise ValueError(f"Task mismatch in {filepath}: {name} != {env_name}")
            for demo in source["data"].values():
                shape = demo["actions"].shape[1:]
                if action_shape is None:
                    action_shape = shape
                elif shape != action_shape:
                    raise ValueError(f"Action shape mismatch in {filepath}: {shape} != {action_shape}")

    # Exclusive creation protects previously collected/merged data.
    with h5py.File(args_cli.output_file, "x") as output:
        episode_idx = 0
        total_samples = 0
        copy_attributes = True

        for filepath in args_cli.input_files:

            with h5py.File(filepath, "r") as input:
                for episode in sorted(input["data"], key=lambda name: int(name.rsplit("_", 1)[-1])):
                    input.copy(f"data/{episode}", output, f"data/demo_{episode_idx}")
                    copied = output[f"data/demo_{episode_idx}"]
                    copied.attrs["merge_source_file"] = os.path.abspath(filepath)
                    copied.attrs["merge_source_episode"] = episode
                    copied.attrs["num_samples"] = len(copied["actions"])
                    total_samples += len(copied["actions"])
                    episode_idx += 1

                if copy_attributes:
                    for key, value in input["data"].attrs.items():
                        output["data"].attrs[key] = value
                    copy_attributes = False
        output["data"].attrs["total"] = total_samples
        env_args = json.loads(output["data"].attrs["env_args"])
        env_args["env_name"] = env_name
        env_args.setdefault("type", 2)
        output["data"].attrs["env_args"] = json.dumps(env_args)

    print(f"Merged {episode_idx} episodes, {total_samples} steps into {args_cli.output_file}")


if __name__ == "__main__":
    merge_datasets()
