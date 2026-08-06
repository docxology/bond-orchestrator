"""bond-orchestrator — Layer 3 mission DAG runner for the BOND suite.

Package identity
    name:     BOND-ORCHESTRATOR
    codename: DAG 00
    layer:    Layer 3 (multi-package mission execution / DAG runner)

The orchestrator executes canned film missions end-to-end over the
:class:`~bond_orchestrator.protocol.MissionProvider` protocol:

    brief() all -> recon() (sequential + deterministic) -> plan() ->
    execute() -> debrief() -> consolidated report

with checkpoint/resume (intermediate reports persisted to a state dir) and
provenance records (written by an independent, deterministic module) for every outcome.

The mathematical core of this package is pure logic: no infrastructure
imports, no I/O inside the protocol/graph modules; I/O lives in the runner's
checkpoint layer, the provenance writer, and the thin CLI.
"""

from __future__ import annotations

from .graph import (
    CycleError,
    FilmGraph,
    GraphError,
    UnknownNodeError,
    build_film_graph,
)
from .missions import (
    MISSION_NAMES,
    MISSIONS,
    OPERATION_DIAMOND,
    OPERATION_OMNIBUS,
    OPERATION_SINGLET,
    UnknownMissionError,
    get_mission,
)
from .planning import Stage, StagePlan, build_stage_plan, plan_stages
from .protocol import (
    BriefRecord,
    Debrief,
    ExecutionResult,
    Mission,
    MissionContext,
    MissionPackage,
    MissionProvider,
    Plan,
    PlanStep,
    ReconReport,
)
from .provenance import (
    ORCHESTRATOR_CODENAME,
    ORCHESTRATOR_IDENTITY,
    PROVENANCE_SCHEMA_VERSION,
    ProvenanceRecord,
    derive_run_id,
    write_mission_report,
    write_outcome_records,
)
from .providers import REFERENCE_PROVIDERS, DeterministicProvider, get_provider
from .film_providers import (
    FilmProviderAdapter,
    FilmProviderError,
    load_film_providers,
    load_mission_providers,
)
from .retry import DEFAULT_RETRY_OUTCOMES, RetryPolicy, RetryRecord, should_retry
from .runner import (
    PHASES,
    MissionError,
    MissionReport,
    MissionRunner,
    ProviderNotFoundError,
)

__version__ = "2.5.2"

IDENTITY = ORCHESTRATOR_IDENTITY
CODENAME = ORCHESTRATOR_CODENAME

__all__ = [
    "BriefRecord",
    "CODENAME",
    "CycleError",
    "DEFAULT_RETRY_OUTCOMES",
    "Debrief",
    "DeterministicProvider",
    "ExecutionResult",
    "FilmGraph",
    "GraphError",
    "IDENTITY",
    "MISSION_NAMES",
    "MISSIONS",
    "Mission",
    "MissionContext",
    "MissionError",
    "MissionPackage",
    "MissionProvider",
    "MissionReport",
    "MissionRunner",
    "OPERATION_DIAMOND",
    "OPERATION_OMNIBUS",
    "OPERATION_SINGLET",
    "ORCHESTRATOR_CODENAME",
    "ORCHESTRATOR_IDENTITY",
    "PHASES",
    "PROVENANCE_SCHEMA_VERSION",
    "Plan",
    "PlanStep",
    "ProvenanceRecord",
    "ProviderNotFoundError",
    "REFERENCE_PROVIDERS",
    "ReconReport",
    "RetryPolicy",
    "RetryRecord",
    "Stage",
    "StagePlan",
    "UnknownMissionError",
    "UnknownNodeError",
    "__version__",
    "build_film_graph",
    "build_stage_plan",
    "derive_run_id",
    "get_mission",
    "get_provider",
    "plan_stages",
    "should_retry",
    "write_mission_report",
    "write_outcome_records",
    "FilmProviderAdapter",
    "FilmProviderError",
    "load_film_providers",
    "load_mission_providers",
]
