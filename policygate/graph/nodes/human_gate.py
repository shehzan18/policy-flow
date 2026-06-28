from __future__ import annotations

from langgraph.types import interrupt

from policygate.graph.state import PRState


def human_gate(state: PRState) -> dict:
    """Pause the graph and surface verified fixes for human approval.

    On first execution interrupt() pauses the whole graph (state is checkpointed
    to Postgres and the process can exit). On resume, interrupt() returns the
    human's decision and execution continues. NOTE: this node re-runs from the
    top on resume, so keep pre-interrupt code minimal.
    """
    verified = [v for v in state["violations"] if v["status"] == "verified"]
    if not verified:
        print("[gate]      nothing verified to approve; skipping")
        return {}

    print(f"[gate]      FREEZING for human review of {len(verified)} fix(es)...")
    decision = interrupt({
        "pr_id": state["pr_id"],
        "fixes": [
            {"rule_id": v["rule_id"], "file": v["file"], "fix": v["proposed_fix"]}
            for v in verified
        ],
    })
    print(f"[gate]      RESUMED with decision: {decision!r}")
    return {"human_decision": decision}