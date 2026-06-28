from __future__ import annotations

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from policygate.rules.catalog import RULES, rules_for
from policygate.graph.state import PRState, PolicyViolation


class _Finding(BaseModel):
    rule_id: str = Field(description="exact rule id from the provided list")
    file: str = Field(description="file path the violation is in")
    line_start: int = Field(description="1-based starting line of the offending code")
    line_end: int = Field(description="1-based ending line of the offending code")
    evidence: str = Field(description="the exact offending code snippet")
    severity: str = Field(description="one of: critical, high, medium")


class _Findings(BaseModel):
    findings: list[_Finding] = Field(default_factory=list)


_model = ChatOpenAI(model="gpt-4o", temperature=0)


def _numbered(content: str) -> str:
    return "\n".join(f"{i + 1}: {line}" for i, line in enumerate(content.splitlines()))


def _detect(state: PRState, category: str) -> dict:
    rules = rules_for(category)
    rules_text = "\n".join(
        f"- {r.id} ({r.name}): {r.description}\n  Detection: {r.detection_guidance}"
        for r in rules
    )
    files_text = "\n\n".join(
        f"### {path}\n{_numbered(content)}" for path, content in state["files"].items()
    )
    prompt = (
        f"You are a strict {category} code reviewer. Find ONLY violations of these rules:\n\n"
        f"{rules_text}\n\n"
        "Rules of engagement:\n"
        "- Report a violation ONLY if it clearly matches one of the rules above.\n"
        "- Use the 1-based line numbers shown at the start of each line.\n"
        "- evidence must be the exact offending snippet.\n"
        "- If there are no violations, return an empty findings list.\n\n"
        f"Files under review:\n\n{files_text}"
    )
    structured = _model.with_structured_output(_Findings)
    result = structured.invoke(prompt)

    violations: list[PolicyViolation] = []
    for f in result.findings:
        if f.rule_id not in RULES:
            continue
        violations.append(PolicyViolation(
            id=f"{f.rule_id}:{f.file}:{f.line_start}",
            rule_id=f.rule_id, severity=f.severity, file=f.file,
            line_start=f.line_start, line_end=f.line_end, evidence=f.evidence,
            status="detected", retries=0, proving_test=None,
            proposed_fix=None, sandbox_result=None,
        ))
    return {"violations": violations}


def security_specialist(state: PRState) -> dict:
    print("[security]  scanning...")
    out = _detect(state, "security")
    print(f"[security]  found {len(out['violations'])}")
    return out


def perf_specialist(state: PRState) -> dict:
    print("[perf]      scanning...")
    out = _detect(state, "performance")
    print(f"[perf]      found {len(out['violations'])}")
    return out


def coverage_specialist(state: PRState) -> dict:
    print("[coverage]  scanning...")
    out = _detect(state, "coverage")
    print(f"[coverage]  found {len(out['violations'])}")
    return out