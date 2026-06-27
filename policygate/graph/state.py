from __future__ import annotations

from typing import Annotated, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages

RuleId = Literal["SEC-SQLI", "SEC-VALIDATION", "PERF-NPLUSONE", "TEST-COVERAGE"]
Severity = Literal["critical", "high", "medium"]
ViolationStatus = Literal[
    "detected", "fix_proposed", "verified", "failed",
    "approved", "rejected", "needs_human",
]


class SandboxResult(TypedDict):
    orig_test_failed: bool   # proving test fails on ORIGINAL code => bug confirmed real
    fix_test_passed: bool    # proving test passes AFTER the fix
    suite_passed: bool       # existing test suite still green => no regression
    logs: str


class PolicyViolation(TypedDict):
    id: str                  # stable id, e.g. f"{rule_id}:{file}:{line_start}"
    rule_id: RuleId
    severity: Severity
    file: str
    line_start: int
    line_end: int
    evidence: str            # the offending snippet
    status: ViolationStatus
    retries: int
    proving_test: Optional[str]
    proposed_fix: Optional[str]
    sandbox_result: Optional[SandboxResult]


def merge_violations(
    existing: list[PolicyViolation],
    incoming: list[PolicyViolation],
) -> list[PolicyViolation]:
    """Upsert violations by id.

    Why custom instead of operator.add: operator.add only *appends*. That's
    perfect for parallel specialists fanning in, but later nodes (fix_generator,
    sandbox_verify) need to UPDATE an existing violation in place. With append
    semantics, returning an updated violation would duplicate it. Keying by id
    gives us both: parallel fan-in AND idempotent in-place updates.
    """
    by_id: dict[str, PolicyViolation] = {v["id"]: v for v in existing}
    for v in incoming:
        by_id[v["id"]] = v
    return list(by_id.values())


class PRState(TypedDict):
    pr_id: str
    repo: str
    branch: str
    diff: str
    files: dict[str, str]                                       # path -> content
    policy: dict                                                # parsed policy.yaml
    violations: Annotated[list[PolicyViolation], merge_violations]
    human_decision: Optional[str]
    messages: Annotated[list, add_messages]