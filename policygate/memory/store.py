from __future__ import annotations

from langgraph.store.base import BaseStore


def _ns(repo: str) -> tuple:
    return ("decisions", repo)


def record_decision(store: BaseStore, repo: str, rule_id: str, decision: str) -> None:
    """Increment this repo's approve/reject tally for a rule (long-term memory)."""
    cur = store.get(_ns(repo), rule_id)
    counts = cur.value if cur else {"approved": 0, "rejected": 0}
    if decision == "approve":
        counts["approved"] += 1
    elif decision == "reject":
        counts["rejected"] += 1
    store.put(_ns(repo), rule_id, counts)


def get_history(store: BaseStore, repo: str, rule_id: str) -> dict:
    """Return {'approved': n, 'rejected': n} for this repo+rule, or zeros."""
    cur = store.get(_ns(repo), rule_id)
    return cur.value if cur else {"approved": 0, "rejected": 0}