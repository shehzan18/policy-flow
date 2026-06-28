from __future__ import annotations

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from policygate.rules.catalog import RULES
from policygate.graph.state import PRState


class _Fix(BaseModel):
    proposed_fix: str = Field(
        description="the FULL corrected file content (entire file, not a diff)")
    proving_test: str = Field(
        description="a complete self-contained pytest file that FAILS on the current "
                    "buggy code and PASSES after the fix is applied")


# cheaper GPT for fixes (your choice). Bump to gpt-4o or Claude if quality is low.
_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _module_name(path: str) -> str:
    return path.rsplit("/", 1)[-1].removesuffix(".py")


def fix_generator(state: PRState) -> dict:
    print("[fix]       generating fixes...")
    updated = []
    for v in state["violations"]:
        if v["status"] != "detected":
            continue
        if RULES[v["rule_id"]].category == "coverage":
            continue  # coverage is a test-addition surfaced to the human, not auto-fixed
        rule = RULES[v["rule_id"]]
        file_content = state["files"].get(v["file"], "")
        module = _module_name(v["file"])

        prompt = (
            f"You are fixing a {rule.name} ({rule.id}) violation.\n\n"
            f"Rule: {rule.description}\n"
            f"Required fix approach: {rule.fix_shape}\n\n"
            f"Violation evidence (around line {v['line_start']} in {v['file']}):\n"
            f"{v['evidence']}\n\n"
            f"Current full content of {v['file']}:\n"
            f"```python\n{file_content}\n```\n\n"
            "Produce TWO things:\n"
            "1. proposed_fix: the ENTIRE corrected file content (apply only the minimal "
            "change needed for this rule; keep everything else identical).\n"
            f"2. proving_test: a complete, self-contained pytest file. It must import the "
            f"function under test from the `{module}` module, set up any fixtures it needs "
            f"(e.g. an in-memory sqlite DB), and assert behaviour that FAILS against the "
            f"current buggy code but PASSES once the fix is applied."
        )

        fix = _model.with_structured_output(_Fix).invoke(prompt)

        nv = dict(v)
        nv["proposed_fix"] = fix.proposed_fix
        nv["proving_test"] = fix.proving_test
        nv["status"] = "fix_proposed"
        updated.append(nv)
        print(f"[fix]       {v['rule_id']} @ {v['file']}:{v['line_start']} -> fix_proposed")

    return {"violations": updated}