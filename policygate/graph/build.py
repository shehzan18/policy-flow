from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from policygate.graph.state import PRState
from policygate.graph.nodes.ingest import ingest
from policygate.graph.nodes.specialists import (
    security_specialist, perf_specialist, coverage_specialist,
)

from policygate.graph.nodes.fix_generator import fix_generator
from policygate.graph.nodes.sandbox_verify import sandbox_verify


# ---- stubs still to be replaced in later parts ----------------------------

def decompose(state: PRState) -> dict:
    print(f"[decompose] splitting {len(state['files'])} file(s) into hunks")
    return {}


def merge_findings(state: PRState) -> dict:
    print(f"[merge]     {len(state['violations'])} violation(s) collected")
    return {}


def report(state: PRState) -> dict:
    print(f"[report]    DONE — {len(state['violations'])} violation(s):")
    for v in state["violations"]:
        print(f"            - {v['rule_id']} @ {v['file']}:{v['line_start']} ({v['status']})")
    return {}


# ---- graph assembly -------------------------------------------------------

def build_graph():
    g = StateGraph(PRState)

    g.add_node("ingest", ingest)
    g.add_node("decompose", decompose)
    g.add_node("security", security_specialist)
    g.add_node("perf", perf_specialist)
    g.add_node("coverage", coverage_specialist)
    g.add_node("merge", merge_findings)
    g.add_node("report", report)
    g.add_node("fix", fix_generator)
    g.add_node("sandbox", sandbox_verify)

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "decompose")

    # fan-out: decompose -> 3 specialists in parallel
    g.add_edge("decompose", "security")
    g.add_edge("decompose", "perf")
    g.add_edge("decompose", "coverage")

    # fan-in: all 3 -> merge
    g.add_edge("security", "merge")
    g.add_edge("perf", "merge")
    g.add_edge("coverage", "merge")

    g.add_edge("merge", "fix")
    g.add_edge("fix", "sandbox")
    g.add_edge("sandbox", "report")
    g.add_edge("report", END)

    return g.compile()


def _empty_state(pr_id: str, repo: str) -> PRState:
    return PRState(
        pr_id=pr_id, repo=repo, branch="main", diff="", files={},
        policy={}, violations=[], human_decision=None, messages=[],
    )


if __name__ == "__main__":
    app = build_graph()
    final = app.invoke(_empty_state(pr_id="1", repo="shehzan18/policy-flow-demo"))
    print(f"\n=== final state has {len(final['violations'])} violations ===")