"""Tests for the deterministic retry policy and its runner integration."""

from __future__ import annotations

import pytest

from bond_orchestrator.missions import OPERATION_OMNIBUS, OPERATION_SINGLET
from bond_orchestrator.protocol import ExecutionResult, MissionProvider
from bond_orchestrator.retry import RetryPolicy, RetryRecord, should_retry
from bond_orchestrator.runner import MissionRunner


class TestRetryPolicy:
    def test_defaults(self) -> None:
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.retry_outcomes == ("failure",)

    def test_rejects_zero_attempts(self) -> None:
        with pytest.raises(ValueError, match="max_attempts"):
            RetryPolicy(max_attempts=0)

    def test_rejects_empty_retry_outcomes(self) -> None:
        with pytest.raises(ValueError, match="retry_outcomes"):
            RetryPolicy(retry_outcomes=())

    def test_as_dict(self) -> None:
        assert RetryPolicy(max_attempts=2).as_dict() == {
            "max_attempts": 2,
            "retry_outcomes": ["failure"],
        }


class TestShouldRetry:
    @staticmethod
    def _results(*outcomes: str) -> tuple[ExecutionResult, ...]:
        return tuple(
            ExecutionResult(
                provider="p",
                package_id="pkg",
                step_index=index,
                action=f"step {index}",
                outcome=outcome,
            )
            for index, outcome in enumerate(outcomes, start=1)
        )

    def test_all_success_never_retries(self) -> None:
        assert not should_retry(self._results("success"), RetryPolicy(max_attempts=3), 1)

    def test_failure_within_attempts_retries(self) -> None:
        assert should_retry(self._results("failure"), RetryPolicy(max_attempts=3), 1)

    def test_attempts_exhausted_stops(self) -> None:
        assert not should_retry(self._results("failure"), RetryPolicy(max_attempts=2), 2)

    def test_non_retryable_outcome_does_not_retry(self) -> None:
        assert not should_retry(self._results("conditional"), RetryPolicy(max_attempts=3), 1)

    def test_any_retryable_outcome_triggers(self) -> None:
        assert should_retry(self._results("success", "failure"), RetryPolicy(max_attempts=3), 1)


class FlakyExecuteDecorator:
    """Real protocol wrapper that deterministically fails its first N executes.

    Wraps any real provider (reference or film adapter); the failure is
    fixed-logic (call counting), not random — retry tests stay deterministic.
    """

    def __init__(self, provider: MissionProvider, fail_attempts: int) -> None:
        self.name = provider.name
        self._provider = provider
        self._fail_attempts = fail_attempts
        self._execute_calls = 0

    def brief(self, package):
        return self._provider.brief(package)

    def recon(self, package, context):
        return self._provider.recon(package, context)

    def plan(self, package, context):
        return self._provider.plan(package, context)

    def execute(self, package, plan, context):
        self._execute_calls += 1
        if self._execute_calls <= self._fail_attempts:
            return tuple(
                ExecutionResult(
                    provider=self.name,
                    package_id=package.id,
                    step_index=step.index,
                    action=step.action,
                    outcome="failure",
                    detail="transient fault",
                )
                for step in plan.steps
            )
        return self._provider.execute(package, plan, context)

    def debrief(self, package, context, plan, results):
        return self._provider.debrief(package, context, plan, results)


def _reference_providers() -> dict[str, MissionProvider]:
    from bond_orchestrator.providers import REFERENCE_PROVIDERS

    return {pid: type(provider)() for pid, provider in REFERENCE_PROVIDERS.items()}


class TestRunnerRetry:
    def test_successful_run_records_no_retries(self) -> None:
        report = MissionRunner(_reference_providers()).run(OPERATION_OMNIBUS)
        assert report.retries == ()
        assert report.retry_count() == 0
        assert "retries:" not in report.consolidated_debrief()

    def test_transient_failure_retried_until_success(self) -> None:
        providers = _reference_providers()
        providers["goldfinger"] = FlakyExecuteDecorator(providers["goldfinger"], fail_attempts=2)
        report = MissionRunner(providers, retry_policy=RetryPolicy(max_attempts=3)).run(OPERATION_OMNIBUS)
        assert report.all_verdicts_pass()
        assert report.retry_count() == 1
        record = report.retries[0]
        assert record == RetryRecord(package_id="goldfinger", phase="execute", attempts=3, succeeded=True)
        assert "retries: goldfinger x3" in report.consolidated_debrief()
        assert report.as_dict()["retries"] == [record.as_dict()]

    def test_persistent_failure_exhausts_attempts(self) -> None:
        providers = _reference_providers()
        providers["goldfinger"] = FlakyExecuteDecorator(providers["goldfinger"], fail_attempts=99)
        report = MissionRunner(providers, retry_policy=RetryPolicy(max_attempts=2)).run(OPERATION_SINGLET)
        assert not report.all_verdicts_pass()
        assert report.retries == (RetryRecord(package_id="goldfinger", phase="execute", attempts=2, succeeded=False),)
        assert report.debriefs[0].verdict == "fail"

    def test_no_policy_means_single_attempt(self) -> None:
        providers = _reference_providers()
        providers["goldfinger"] = FlakyExecuteDecorator(providers["goldfinger"], fail_attempts=99)
        report = MissionRunner(providers).run(OPERATION_SINGLET)
        assert report.retries == ()
        assert report.debriefs[0].verdict == "fail"

    def test_deterministic_across_runs(self) -> None:
        def run_once() -> dict[str, object]:
            providers = _reference_providers()
            providers["goldfinger"] = FlakyExecuteDecorator(providers["goldfinger"], fail_attempts=1)
            return MissionRunner(providers, retry_policy=RetryPolicy(max_attempts=3)).run(OPERATION_SINGLET).as_dict()

        assert run_once() == run_once()

    def test_retry_attempts_persist_across_checkpoint_resume(self, tmp_path) -> None:
        checkpoint_dir = tmp_path / "state"

        def run_with_flaky() -> dict[str, object]:
            providers = _reference_providers()
            providers["goldfinger"] = FlakyExecuteDecorator(providers["goldfinger"], fail_attempts=2)
            return (
                MissionRunner(providers, checkpoint_dir=checkpoint_dir, retry_policy=RetryPolicy(max_attempts=3))
                .run(OPERATION_SINGLET)
                .as_dict()
            )

        first = run_with_flaky()
        assert first["retries"] == [{"package_id": "goldfinger", "phase": "execute", "attempts": 3, "succeeded": True}]
        # A resumed run replays the retry record from the checkpoint file.
        resumed = run_with_flaky()
        assert resumed == first
        execute_record = (checkpoint_dir / "OPERATION_SINGLET" / "execute_goldfinger.json").read_text()
        assert '"attempts": 3' in execute_record


class TestFlakyDecoratorContract:
    def test_decorator_implements_protocol(self) -> None:
        from bond_orchestrator.protocol import MissionProvider

        provider = _reference_providers()["goldfinger"]
        wrapped = FlakyExecuteDecorator(provider, fail_attempts=1)
        assert isinstance(wrapped, MissionProvider)
