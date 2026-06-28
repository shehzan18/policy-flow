from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    category: str          # security | performance | coverage
    description: str
    detection_guidance: str
    fix_shape: str         # used in Part 4 (fix generation)


RULES: dict[str, Rule] = {
    "SEC-SQLI": Rule(
        id="SEC-SQLI",
        name="SQL injection via string building",
        category="security",
        description="A SQL query is built using string concatenation, f-strings, "
                    "or % formatting with untrusted input, instead of parameters.",
        detection_guidance="Look for SQL strings assembled with +, f-strings, .format(), "
                           "or % that interpolate variables, then passed to execute(). "
                           "A query that uses parameterized placeholders (?, %s with params) is SAFE.",
        fix_shape="Rewrite as a parameterized query: use ? placeholders and pass values "
                  "as the second argument to execute().",
    ),
    "SEC-VALIDATION": Rule(
        id="SEC-VALIDATION",
        name="Missing input validation on handler",
        category="security",
        description="An endpoint/handler reads request input and uses it without validating "
                    "type/shape first.",
        detection_guidance="Look for request/body/params data used directly without a Pydantic "
                           "model or explicit validation guard. Only flag actual request handlers.",
        fix_shape="Introduce a Pydantic model for the input and validate before use.",
    ),
    "PERF-NPLUSONE": Rule(
        id="PERF-NPLUSONE",
        name="N+1 query in a loop",
        category="performance",
        description="A database query is executed once per iteration of a loop over rows/objects.",
        detection_guidance="Look for a loop whose body issues a DB call (execute/query/get) per "
                           "iteration. A single batched/joined query outside the loop is SAFE.",
        fix_shape="Replace the per-iteration queries with a single batched or joined query.",
    ),
    "TEST-COVERAGE": Rule(
        id="TEST-COVERAGE",
        name="New code without a test",
        category="coverage",
        description="A newly added or modified non-trivial function in a non-test file has no "
                    "corresponding unit test in the provided files.",
        detection_guidance="Only flag functions defined in NON-test files (filename does not "
                           "start with test_ and is not in a tests/ dir) when no test file in the "
                           "provided set references them. Skip trivial one-liners.",
        fix_shape="Generate a pytest unit test that exercises the function's core behavior.",
    ),
}


def rules_for(category: str) -> list[Rule]:
    return [r for r in RULES.values() if r.category == category]