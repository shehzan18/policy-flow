from __future__ import annotations

import os
from dataclasses import dataclass

from github import Auth, Github


@dataclass
class ChangedFile:
    path: str
    status: str              # added | modified | removed
    patch: str | None        # unified-diff hunk for this file
    content: str             # full file content at PR head ("" if removed)


@dataclass
class PRData:
    pr_id: str
    repo: str
    branch: str
    diff: str                # all per-file patches concatenated
    files: dict[str, str]    # path -> full content
    changed: list[ChangedFile]


def _client() -> Github:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set in .env")
    return Github(auth=Auth.Token(token))


def fetch_pr(repo_full_name: str, pr_number: int, py_only: bool = True) -> PRData:
    """Pull a PR's changed Python files + diff + content into a PRData."""
    gh = _client()
    repo = gh.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    changed: list[ChangedFile] = []
    files: dict[str, str] = {}
    diff_parts: list[str] = []

    for f in pr.get_files():
        if py_only and not f.filename.endswith(".py"):
            continue

        content = ""
        if f.status != "removed":
            try:
                blob = repo.get_contents(f.filename, ref=pr.head.sha)
                content = blob.decoded_content.decode("utf-8", "replace")
            except Exception:
                content = ""

        if f.patch:
            diff_parts.append(f"--- {f.filename}\n{f.patch}")

        changed.append(ChangedFile(
            path=f.filename, status=f.status, patch=f.patch, content=content,
        ))
        if content:
            files[f.filename] = content

    return PRData(
        pr_id=str(pr_number),
        repo=repo_full_name,
        branch=pr.head.ref,
        diff="\n\n".join(diff_parts),
        files=files,
        changed=changed,
    )

def post_pr_comment(repo_full_name: str, pr_number: int, body: str) -> None:
    """Post a comment on a PR (used to deliver verified fixes / rejection feedback)."""
    gh = _client()
    pr = gh.get_repo(repo_full_name).get_pull(pr_number)
    pr.create_issue_comment(body)

def list_python_files(repo_full_name: str, limit: int = 30) -> list[str]:
    """List .py file paths in a repo (skips tests/migrations) via the git tree."""
    gh = _client()
    repo = gh.get_repo(repo_full_name)
    tree = repo.get_git_tree(repo.default_branch, recursive=True).tree
    paths = [
        t.path for t in tree
        if t.type == "blob" and t.path.endswith(".py")
        and "test" not in t.path.lower() and "migration" not in t.path.lower()
        and not t.path.endswith("__init__.py")
    ]
    return paths[:limit]


def fetch_files(repo_full_name: str, paths: list[str]) -> dict:
    """Fetch the content of specific files from a repo's default branch."""
    gh = _client()
    repo = gh.get_repo(repo_full_name)
    out = {}
    for p in paths:
        try:
            blob = repo.get_contents(p)
            out[p] = blob.decoded_content.decode("utf-8", "replace")
        except Exception:
            pass
    return out