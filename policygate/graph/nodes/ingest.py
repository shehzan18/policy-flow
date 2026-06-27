from __future__ import annotations

from policygate.github.client import fetch_pr
from policygate.graph.state import PRState


def ingest(state: PRState) -> dict:
    """Fetch the real PR's diff + changed Python files into state."""
    pr = fetch_pr(state["repo"], int(state["pr_id"]))
    print(f"[ingest]    PR #{pr.pr_id} on {pr.repo} (branch: {pr.branch})")
    print(f"[ingest]    {len(pr.files)} Python file(s) changed: {list(pr.files)}")
    return {
        "branch": pr.branch,
        "diff": pr.diff,
        "files": pr.files,
    }