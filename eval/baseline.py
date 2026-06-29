"""Naive single-LLM baseline, scored on the same benchmark as the pipeline.

Run:  python eval/baseline.py
Reports the agentic pipeline vs. a single 'review everything at once' LLM call,
so you can quantify what the multi-agent + structured design actually buys you.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from policygate.rules.catalog import RULES
from eval.scorer import score, _detect_all

# the 3 defect rules the pipeline enforces (coverage excluded, same as scorer)
DEFECT_RULES = {rid: r for rid, r in RULES.items() if r.category != "coverage"}


class _BFinding(BaseModel):
    rule_id: str = Field(description="one of the listed rule ids")
    file: str


class _BFindings(BaseModel):
    findings: list[_BFinding] = Field(default_factory=list)


_model = ChatOpenAI(model="gpt-4o", temperature=0)


def _numbered(content: str) -> str:
    return "\n".join(f"{i + 1}: {line}" for i, line in enumerate(content.splitlines()))


def baseline_detect(files: dict) -> set:
    """One LLM call, all rules, all files at once — the naive approach."""
    rules_text = "\n".join(f"- {r.id}: {r.description}" for r in DEFECT_RULES.values())
    files_text = "\n\n".join(f"### {p}\n{_numbered(c)}" for p, c in files.items())
    prompt = (
        "You are a code reviewer. Review the files and report ALL violations of "
        f"these rules:\n{rules_text}\n\n"
        "Return one finding per violation (rule_id + file). If none, return empty.\n\n"
        f"{files_text}"
    )
    result = _model.with_structured_output(_BFindings).invoke(prompt)
    return {(f.rule_id, f.file) for f in result.findings if f.rule_id in DEFECT_RULES}


def _fmt(label, r):
    return f"  {label:22s} precision={r['precision']:.2f}  recall={r['recall']:.2f}  f1={r['f1']:.2f}"


if __name__ == "__main__":
    print("=== Scoring agentic pipeline ===")
    pipeline = score(_detect_all, verbose=False)
    print("=== Scoring naive single-LLM baseline ===")
    baseline = score(baseline_detect, verbose=False)

    print("\n" + "=" * 60)
    print("  PolicyGate: agentic pipeline vs. naive single-LLM baseline")
    print("=" * 60)
    print(_fmt("naive baseline", baseline))
    print(_fmt("agentic pipeline", pipeline))
    lift = pipeline["f1"] - baseline["f1"]
    print(f"\n  F1 lift from the agentic design: {lift:+.2f}")