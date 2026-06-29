from __future__ import annotations

from policygate.github.client import fetch_pr
from policygate.graph.state import PRState
from policygate.github.client import fetch_files


def ingest(state: PRState) -> dict:
    if state.get("files"):
        print(f"[ingest]    using {len(state['files'])} pre-loaded file(s) (scan mode)")
        return {}
    
    pr = fetch_pr(state["repo"], int(state["pr_id"]))
    
    requirements = fetch_files(state["repo"], ["requirements.txt"]).get("requirements.txt", "")
    print(f"[ingest]    PR #{pr.pr_id} on {pr.repo} (branch: {pr.branch})")
    print(f"[ingest]    {len(pr.files)} Python file(s) changed: {list(pr.files)}")
    return {
        "branch": pr.branch,
        "diff": pr.diff,
        "files": pr.files,
    }