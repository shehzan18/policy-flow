from __future__ import annotations

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from policygate.rules.catalog import RULES
from policygate.graph.state import PRState

MAX_RETRIES = 2


class _Fix(BaseModel):
    proposed_fix: str = Field(description="the FULL corrected file content (entire file, not a diff)")
    proving_test: str = Field(description="a complete self-contained pytest file that FAILS on the "
                                          "current buggy code and PASSES after the fix is applied")


_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _module_name(path: str) -> str:
    return path.rsplit("/", 1)[-1].removesuffix(".py")


def fix_generator(state: PRState) -> dict:
    print("[fix]       generating fixes...")
    updated = []
    for v in state["violations"]:
        is_first = v["status"] == "detected"
        is_retry = v["status"] == "failed" and v["retries"] < MAX_RETRIES
        if not (is_first or is_retry):
            continue
        if RULES[v["rule_id"]].category == "coverage":
            continue

        rule = RULES[v["rule_id"]]
        file_content = state["files"].get(v["file"], "")
        module = _module_name(v["file"])

        retry_note = ""
        if is_retry:
            prev_logs = (v.get("sandbox_result") or {}).get("logs", "")
            retry_note = (
                f"\n\nYOUR PREVIOUS ATTEMPT FAILED verification. Sandbox output:\n"
                f"{prev_logs}\n"
                "Fix the root cause of that failure this time."
            )

        prompt = (
            f"You are fixing a {rule.name} ({rule.id}) violation.\n\n"
            f"Rule: {rule.description}\n"
            f"Required fix approach: {rule.fix_shape}\n\n"
            f"Violation evidence (around line {v['line_start']} in {v['file']}):\n{v['evidence']}\n\n"
            f"Current full content of {v['file']}:\n```python\n{file_content}\n```\n\n"
            "Produce TWO things:\n"
            "1. proposed_fix: the ENTIRE corrected file content (minimal change for this rule).\n"
            f"2. proving_test: a complete self-contained pytest file importing from the `{module}` "
            "module, that FAILS on the current buggy code but PASSES after the fix."
            f"{retry_note}"
        )

        fix = _model.with_structured_output(_Fix).invoke(prompt)
        nv = dict(v)
        nv["proposed_fix"] = fix.proposed_fix
        nv["proving_test"] = fix.proving_test
        nv["status"] = "fix_proposed"
        if is_retry:
            nv["retries"] = v["retries"] + 1
        updated.append(nv)
        tag = f"retry {nv['retries']}" if is_retry else "first attempt"
        print(f"[fix]       {v['rule_id']} @ {v['file']}:{v['line_start']} -> fix_proposed ({tag})")

    return {"violations": updated}