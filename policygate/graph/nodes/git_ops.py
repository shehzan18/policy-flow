from __future__ import annotations

from policygate.graph.state import PRState
from policygate.github.client import post_pr_comment
from langgraph.store.base import BaseStore
from policygate.memory.store import record_decision


def _approval_comment(v: dict) -> str:
    sr = v.get("sandbox_result") or {}
    return (
        f"## 🛡️ PolicyGate — verified fix for `{v['rule_id']}`\n\n"
        f"**File:** `{v['file']}` (line {v['line_start']})\n\n"
        f"**Sandbox proof:** proving test failed on the original code "
        f"(`orig_failed={sr.get('orig_test_failed')}`) and passed after the fix "
        f"(`fix_passed={sr.get('fix_test_passed')}`).\n\n"
        f"**Suggested fix:**\n```python\n{v['proposed_fix']}\n```\n\n"
        f"_Approved by a human reviewer via PolicyGate._"
    )


def _rejection_comment(v: dict) -> str:
    return (
        f"## PolicyGate — fix for `{v['rule_id']}` was rejected\n\n"
        f"A reviewer declined the auto-generated fix for `{v['file']}`. "
        f"Recorded for future learning."
    )


def git_ops(state: PRState, *, store: BaseStore) -> dict:
    decision = state.get("human_decision")
    verified = [v for v in state["violations"] if v["status"] == "verified"]
    if not verified:
        print("[git_ops]   nothing to act on")
        return {}

    updated = []
    for v in verified:
        if decision == "approve":
            post_pr_comment(state["repo"], int(state["pr_id"]), _approval_comment(v))
            nv = dict(v); nv["status"] = "approved"
            print(f"[git_ops]   {v['rule_id']} -> APPROVED (review posted to PR)")
        elif decision == "reject":
            post_pr_comment(state["repo"], int(state["pr_id"]), _rejection_comment(v))
            nv = dict(v); nv["status"] = "rejected"
            print(f"[git_ops]   {v['rule_id']} -> REJECTED (feedback recorded)")
        else:
            nv = dict(v)
        
        if decision in ("approve", "reject"):
            record_decision(store, state["repo"], v["rule_id"], decision)
        updated.append(nv)
        
    return {"violations": updated}