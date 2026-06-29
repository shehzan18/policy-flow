from __future__ import annotations

from langgraph.store.base import BaseStore
from langgraph.types import interrupt

from policygate.graph.state import PRState
from policygate.memory.store import get_history


def human_gate(state: PRState, *, store: BaseStore) -> dict:
    """Pause for human approval, surfacing this team's prior decisions per rule."""
    verified = [v for v in state["violations"] if v["status"] == "verified"]
    if not verified:
        print("[gate]      nothing verified to approve; skipping")
        return {}

    # recall long-term memory: how has this team treated each rule before?
    fixes = []
    for v in verified:
        h = get_history(store, state["repo"], v["rule_id"])
        print(f"[gate]      memory: {v['rule_id']} on this repo -> "
              f"approved {h['approved']}, rejected {h['rejected']}")
        fixes.append({
            "rule_id": v["rule_id"], "file": v["file"],
            "fix": v["proposed_fix"], "history": h,
        })

    print(f"[gate]      FREEZING for human review of {len(verified)} fix(es)...")
    decision = interrupt({"pr_id": state["pr_id"], "fixes": fixes})
    print(f"[gate]      RESUMED with decision: {decision!r}")
    return {"human_decision": decision}