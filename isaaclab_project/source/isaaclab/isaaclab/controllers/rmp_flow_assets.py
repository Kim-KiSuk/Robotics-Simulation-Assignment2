# Copyright (c) 2022-2025, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Resolve RMPFlow assets once into a controller-owned download directory."""

from collections.abc import Callable
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import yaml


class RmpFlowAssetSnapshot:
    """Keep remote configuration files stable while Lula creates/resets policies.

    The shared /tmp/<basename> download paths can be overwritten by another
    simulation. Each controller instead owns its download paths, and subsequent
    environment resets reuse the same validated files. Local paths retain their
    original locations, preserving relative references in user robot assets.
    """

    def __init__(self):
        self._directory = tempfile.TemporaryDirectory(prefix="isaaclab_rmpflow_")
        self._paths = None

    def resolve(self, cfg, retrieve_file: Callable) -> tuple[str, str, str]:
        if self._paths is not None:
            return self._paths
        paths = {}
        for role in ("urdf_file", "collision_file", "config_file"):
            paths[role] = retrieve_file(
                getattr(cfg, role),
                download_dir=str(Path(self._directory.name) / role),
                force_download=True,
            )
        self._validate(paths, cfg)
        self._paths = (paths["urdf_file"], paths["collision_file"], paths["config_file"])
        return self._paths

    @staticmethod
    def _validate(paths, cfg):
        for role in ("collision_file", "config_file"):
            path = paths[role]
            try:
                document = yaml.safe_load(Path(path).read_text())
                if not isinstance(document, dict) or not document:
                    raise ValueError("expected a nonempty YAML mapping")
                if role == "config_file":
                    for key in ("rmp_params", "canonical_resolve"):
                        if not isinstance(document.get(key), dict) or not document[key]:
                            raise ValueError(f"missing or invalid '{key}' mapping")
            except (OSError, ValueError, yaml.YAMLError) as error:
                raise ValueError(
                    f"Invalid RMPFlow {role}: source={getattr(cfg, role)!r}, local={path!r}: {error}"
                ) from error
        try:
            root = ET.parse(paths["urdf_file"]).getroot()
            if root.tag != "robot":
                raise ValueError("expected a URDF <robot> root")
        except (OSError, ValueError, ET.ParseError) as error:
            raise ValueError(f"Invalid RMPFlow URDF: {paths['urdf_file']!r}: {error}") from error
