"""Deterministic retry policy for mission step execution (pure core).

Retries are immediate and deterministic — there is NO wall-clock backoff,
because a sleep would break the byte-determinism of reports, checkpoint
files, and provenance records (a guardrail of this package).  The policy only
bounds how many attempts a failing ``execute`` step is given and which
outcomes are considered retryable.

The runner applies the policy to the ``execute`` phase: when any execution
result carries a retryable outcome, the step is re-executed (attempt N+1)
until it succeeds or ``max_attempts`` are exhausted.  Every completed execute
step records its attempt count in the checkpoint record and — when more than
one attempt was needed — a :class:`RetryRecord` in the mission report.
"""

from __future__ import annotations

from dataclasses import dataclass

from .protocol import ExecutionResult

DEFAULT_RETRY_OUTCOMES = ("failure",)


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded, deterministic retry policy.

    Attributes:
        max_attempts: Maximum number of execute attempts per package step
            (>= 1; 1 means "no retry").
        retry_outcomes: Outcomes that trigger another attempt (default:
            ``("failure",)``).
    """

    max_attempts: int = 3
    retry_outcomes: tuple[str, ...] = DEFAULT_RETRY_OUTCOMES

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if not self.retry_outcomes:
            raise ValueError("retry_outcomes must not be empty")

    def as_dict(self) -> dict[str, object]:
        """Deterministic serialization of the policy."""
        return {"max_attempts": self.max_attempts, "retry_outcomes": list(self.retry_outcomes)}


@dataclass(frozen=True)
class RetryRecord:
    """One package step's retry outcome, recorded when attempts > 1.

    Attributes:
        package_id: The package whose step was retried.
        phase: The phase that was retried (always ``"execute"`` today).
        attempts: Total attempts used (1 = no retry needed; only attempts > 1
            produce a record).
        succeeded: Whether the final attempt succeeded.
    """

    package_id: str
    phase: str
    attempts: int
    succeeded: bool

    def as_dict(self) -> dict[str, object]:
        """Deterministic serialization of the record."""
        return {
            "package_id": self.package_id,
            "phase": self.phase,
            "attempts": self.attempts,
            "succeeded": self.succeeded,
        }


def should_retry(
    results: tuple[ExecutionResult, ...],
    policy: RetryPolicy,
    attempts_used: int,
) -> bool:
    """True when another attempt is permitted and any outcome is retryable.

    Args:
        results: The execution results of the latest attempt.
        policy: The active retry policy.
        attempts_used: Number of attempts already made (>= 1).
    """
    if attempts_used >= policy.max_attempts:
        return False
    return any(result.outcome in policy.retry_outcomes for result in results)
