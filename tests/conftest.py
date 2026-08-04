"""Shared pytest fixtures for bond-orchestrator.

Zero-mock policy: every test exercises real classes implementing the real
:class:`~bond_orchestrator.protocol.MissionProvider` protocol with
deterministic logic.  This file only provides path bootstrap and fixtures.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bond_orchestrator.missions import (  # noqa: E402
    OPERATION_DIAMOND,
    OPERATION_OMNIBUS,
    OPERATION_SINGLET,
)
from bond_orchestrator.protocol import Mission, MissionProvider  # noqa: E402
from bond_orchestrator.providers import REFERENCE_PROVIDERS  # noqa: E402
from bond_orchestrator.runner import MissionRunner  # noqa: E402


@pytest.fixture
def project_root() -> Path:
    """The bond-orchestrator package root."""
    return PROJECT_ROOT


@pytest.fixture
def reference_providers() -> dict[str, MissionProvider]:
    """The deterministic reference providers keyed by package id."""
    return dict(REFERENCE_PROVIDERS)


@pytest.fixture
def omnibus_runner() -> MissionRunner:
    """A runner bound to the reference providers, no checkpoint dir."""
    return MissionRunner(REFERENCE_PROVIDERS)


@pytest.fixture
def diamond_runner() -> MissionRunner:
    """A runner for the diamond-shaped mission, no checkpoint dir."""
    return MissionRunner(REFERENCE_PROVIDERS)


@pytest.fixture
def singleton_runner() -> MissionRunner:
    """A runner for the single-package mission, no checkpoint dir."""
    return MissionRunner(REFERENCE_PROVIDERS)


@pytest.fixture
def missions() -> tuple[Mission, Mission, Mission]:
    """The three canned missions, in registry order."""
    return OPERATION_OMNIBUS, OPERATION_DIAMOND, OPERATION_SINGLET
