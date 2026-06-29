import sys
import os

from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from policygate.graph.state import PRState
from policygate.graph.build import decompose, merge_findings, report, MAX_RETRIES
from policygate.graph.nodes.ingest import ingest
from policygate.graph.nodes.specialists import security_specialist, perf_specialist
from policygate.graph.nodes.fix_generator import fix_generator
from policygate.graph.nodes.sandbox_verify import sandbox_verify
from policygate.github.client import list_python_files, fetch_files

SQL_HINTS = ("execute(", "SELECT", ".format(", "cursor", "query")


def _scan_route(state: PRState) -> str:
    for v in state["violations"]:
        if v["status"] == "failed" and v["retries"] < MAX_RETRIES:
            return "fix"
    return "report"


def build_scan_graph():
    g = StateGraph(PRState)
    g.add_node("ingest", ingest)
    g.add_node("decompose", decompose)
    g.add_node("security", security_specialist)
    g.add_node("perf", perf_specialist)
    g.add_node("merge", merge_findings)
    g.add_node("fix", fix_generator)
    g.add_node("sandbox", sandbox_verify)
    g.add_node("report", report)
    g.add_edge(START, "ingest")
    g.add_edge("ingest", "decompose")
    g.add_edge("decompose", "security")
    g.add_edge("decompose", "perf")
    g.add_edge("security", "merge")
    g.add_edge("perf", "merge")
    g.add_edge("merge", "fix")
    g.add_edge("fix", "sandbox")
    g.add_conditional_edges("sandbox", _scan_route, {"fix": "fix", "report": "report"})
    g.add_edge("report", END)
    return g.compile(checkpointer=InMemorySaver())


def main():
    if len(sys.argv) < 2:
        print('usage: python scan.py <owner/repo>   e.g. python scan.py JasonHinds13/hackable')
        return
    repo = sys.argv[1]

    all_py = list_python_files(repo)
    print(f"found {len(all_py)} python files in {repo}")
    # fetch a slice, prefer files that look SQL-ish to maximize hitting our rules
    candidate = fetch_files(repo, all_py[:12])
    relevant = {p: c for p, c in candidate.items() if any(h in c for h in SQL_HINTS)}
    files = relevant or dict(list(candidate.items())[:3])
    print(f"scanning {len(files)} file(s): {list(files)}")

    # fetch the repo's requirements so the sandbox can install deps before verifying
    requirements = fetch_files(repo, ["requirements.txt"]).get("requirements.txt", "")
    if requirements:
        print(f"found requirements.txt ({len(requirements.splitlines())} deps) — will install in sandbox")
    print()

    app = build_scan_graph()
    state = PRState(pr_id="scan", repo=repo, branch="", diff="", files=files,
                    policy={}, requirements=requirements, violations=[],
                    human_decision=None, messages=[])
    result = app.invoke(state, config={"configurable": {"thread_id": f"scan-{repo}"}})

    print("\n=== SCAN RESULT ===")
    if not result["violations"]:
        print("No violations of the enforced rules found.")
    for v in result["violations"]:
        print(f"  - {v['rule_id']} @ {v['file']}:{v['line_start']} [{v['status']}]")
        sr = v.get("sandbox_result")
        if sr and not (sr["orig_test_failed"] and sr["fix_test_passed"]):
            print(f"      (fix unverified: {sr['logs'][:120]}...)")


if __name__ == "__main__":
    main()