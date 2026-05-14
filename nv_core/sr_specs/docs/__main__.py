# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""
CLI entry point for simready.foundation.core.

Usage:
    python -m simready.foundation.core [options] ASSET

Registers all SimReady capabilities, features and validation rules, then
delegates to the omni.asset_validator CLI. All standard flags apply, e.g.:

    python -m simready.foundation.core --feature FET000_CORE asset.usda
    python -m simready.foundation.core --capability atomic_asset asset.usda
"""
from __future__ import annotations

import logging

from omni.asset_validator import CapabilityRegistry, FeatureRegistry, cli_main
from omni.capabilities import Capabilities, Features

logger = logging.getLogger(__name__)


def main() -> None:
    # Import capabilities to trigger @register_rule / @register_requirements decorators.
    from . import capabilities  # noqa: F401

    cap_registry = CapabilityRegistry()
    for capability in Capabilities:
        try:
            cap_registry.add(capability)
        except Exception:
            logger.debug(f"Capability {capability.name} already registered, skipping.")

    feat_registry = FeatureRegistry()
    for feature in Features:
        try:
            feat_registry.add(feature)
        except Exception:
            logger.debug(f"Feature {feature.name} already registered, skipping.")

    cli_main()


if __name__ == "__main__":
    main()
