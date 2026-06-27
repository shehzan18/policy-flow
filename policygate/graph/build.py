from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from policygate.graph.state import PRState, PolicyViolation


# ---- stub nodes (Part 1: fake logic, real wiring) -------------------------
# Each returns a partial state update. We replace these one by one in later parts.

def ingest(state: PRState) -> dict:
    print(f"[ingest]    PR #{state['pr_id']} on {state['repo']}")
    # later: fetch real diff + files from GitHub
    return {"files": {"app.py": "# fake file content"}}


def decompose(state: PRState) -> dict:
    print(f"[decompose] splitting {len(state['files'])} file(s) into hunks")
    return {}


def security_specialist(state: PRState) -> dict:
    print("[security]  scanning...")
    return {"violations": [_stub_violation("SEC-SQLI", "app.py", 10)]}


def perf_specialist(state: PRState) -> dict:
    print("[perf]      scanning...")
    return {"violations": [_stub_violation("PERF-NPLUSONE", "app.py", 25)]}


def coverage_specialist(state: PRState) -> dict:
    print("[coverage]  scanning...")
    return {"violations": [_stub_violation("TEST-COVERAGE", "app.py", 40)]}


def merge_findings(state: PRState) -> dict:
    print(f"[merge]     {len(state['violations'])} violation(s) collected")
    return {}


def report(state: PRState) -> dict:
    print(f"[report]    DONE — {len(state['violations'])} violation(s):")
    for v in state["violations"]:
        print(f"            - {v['rule_id']} @ {v['file']}:{v['line_start']} ({v['status']})")
    return {}


def _stub_violation(rule_id, file, line) -> PolicyViolation:
    return PolicyViolation(
        id=f"{rule_id}:{file}:{line}", rule_id=rule_id, severity="high",
        file=file, line_start=line, line_end=line, evidence="<stub>",
        status="detected", retries=0, proving_test=None,
        proposed_fix=None, sandbox_result=None,
    )


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

    g.add_edge("merge", "report")
    g.add_edge("report", END)

    return g.compile()


def _empty_state(pr_id: str, repo: str) -> PRState:
    return PRState(
        pr_id=pr_id, repo=repo, branch="main", diff="", files={},
        policy={}, violations=[], human_decision=None, messages=[],
    )


if __name__ == "__main__":
    app = build_graph()
    print("=== running PolicyGate skeleton on fake data ===\n")
    final = app.invoke(_empty_state(pr_id="42", repo="shehzan18/demo"))
    print(f"\n=== final state has {len(final['violations'])} violations ===")