import os

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import streamlit as st
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langgraph.types import Command

from policygate.graph.build import build_graph, _empty_state
from policygate.graph.nodes.specialists import security_specialist, perf_specialist
from policygate.github.client import list_python_files, fetch_files

URL = os.environ["DATABASE_URL"]
REPO = "shehzan18/policy-flow-demo"
SQL_HINTS = ("execute(", "SELECT", ".format(", "cursor", "query")

st.set_page_config(page_title="PolicyGate", page_icon="🛡️", layout="wide")
st.title("🛡️ PolicyGate")
st.caption("Autonomous PR policy-enforcement agent · detect → fix → sandbox-verify → human gate · built on LangGraph")

tab_run, tab_queue, tab_mem, tab_eval, tab_scan = st.tabs(
    ["🚀 Run", "✅ Review Queue", "🧠 Memory", "📊 Eval", "🔍 Scan Repo"]
)


# ---------------------------------------------------------------- RUN
with tab_run:
    st.subheader("Run the enforcement pipeline on a PR")
    col_a, col_b = st.columns([1, 3])
    pr_id = col_a.text_input("PR number", value="1")
    run = col_a.button("▶ Run PolicyGate", type="primary")

    if run:
        stages = col_b.empty()
        seen = []
        try:
            with PostgresSaver.from_conn_string(URL) as saver, \
                 PostgresStore.from_conn_string(URL) as store:
                saver.setup(); store.setup()
                app = build_graph(checkpointer=saver, store=store)
                cfg = {"configurable": {"thread_id": f"pr-{pr_id}"}}
                try:
                    saver.delete_thread(f"pr-{pr_id}")
                except Exception:
                    pass

                with st.status("Running pipeline...", expanded=True) as status:
                    label = {"ingest": "Ingesting PR from GitHub",
                             "decompose": "Decomposing diff",
                             "security": "Security specialist scanning",
                             "perf": "Performance specialist scanning",
                             "merge": "Merging findings",
                             "fix": "Generating fixes",
                             "sandbox": "Verifying fixes in E2B sandbox",
                             "gate": "Freezing for human review"}
                    for chunk in app.stream(_empty_state(pr_id=pr_id, repo=REPO),
                                            config=cfg, stream_mode="updates"):
                        for node in chunk:
                            if node == "__interrupt__":
                                st.write("⏸️ Frozen — awaiting human approval")
                            else:
                                st.write(f"✓ {label.get(node, node)}")
                    status.update(label="Pipeline run complete", state="complete")

                violations = app.get_state(cfg).values.get("violations", [])
            st.session_state["last_run"] = violations
        except Exception as e:
            st.error(f"Run failed: {e}")

    violations = st.session_state.get("last_run", [])
    if violations:
        st.markdown("### Findings")
        for v in violations:
            icon = {"verified": "🟢", "approved": "🟢", "failed": "🔴",
                    "detected": "🟡", "fix_proposed": "🟡"}.get(v["status"], "⚪")
            with st.expander(f"{icon} {v['rule_id']} · {v['file']}:{v['line_start']} · "
                             f"{v['severity']} · [{v['status']}]"):
                st.markdown("**Evidence**")
                st.code(v["evidence"])
                if v.get("proposed_fix"):
                    st.markdown("**Proposed fix**")
                    st.code(v["proposed_fix"], language="python")
                if v.get("proving_test"):
                    st.markdown("**Proving test**")
                    st.code(v["proving_test"], language="python")
                sr = v.get("sandbox_result")
                if sr:
                    st.markdown("**Sandbox proof**")
                    st.write(f"- test failed on original: `{sr['orig_test_failed']}`")
                    st.write(f"- test passed after fix: `{sr['fix_test_passed']}`")


# ---------------------------------------------------------------- QUEUE
def _list_pending(saver, app):
    seen = {}
    for ck in saver.list(None):
        seen[ck.config["configurable"]["thread_id"]] = True
    pending = []
    for tid in seen:
        cfg = {"configurable": {"thread_id": tid}}
        snap = app.get_state(cfg)
        interrupts = [i for t in snap.tasks for i in (t.interrupts or [])]
        if snap.next and interrupts:
            pending.append((tid, interrupts[0].value))
    return pending


with tab_queue:
    st.subheader("PRs awaiting human approval")
    try:
        with PostgresSaver.from_conn_string(URL) as saver, \
             PostgresStore.from_conn_string(URL) as store:
            saver.setup(); store.setup()
            app = build_graph(checkpointer=saver, store=store)
            pending = _list_pending(saver, app)

            if not pending:
                st.success("Queue empty — nothing awaiting review. 🎉")
            for thread_id, payload in pending:
                with st.container(border=True):
                    st.markdown(f"#### PR #{payload.get('pr_id','?')} · "
                                f"{len(payload.get('fixes', []))} verified fix(es)")
                    for f in payload.get("fixes", []):
                        st.markdown(f"**`{f['rule_id']}`** in `{f['file']}`")
                        h = f.get("history") or {}
                        if h:
                            st.caption(f"Team history for this rule — approved "
                                       f"{h.get('approved',0)}, rejected {h.get('rejected',0)}")
                        st.code(f["fix"], language="python")
                    c1, c2, _ = st.columns([1, 1, 5])
                    if c1.button("✅ Approve", key=f"a-{thread_id}", type="primary"):
                        app.invoke(Command(resume="approve"),
                                   config={"configurable": {"thread_id": thread_id}})
                        st.success("Approved — fix posted to the PR."); st.rerun()
                    if c2.button("❌ Reject", key=f"r-{thread_id}"):
                        app.invoke(Command(resume="reject"),
                                   config={"configurable": {"thread_id": thread_id}})
                        st.warning("Rejected — feedback recorded."); st.rerun()
    except Exception as e:
        st.error(f"Could not load queue: {e}")


# ---------------------------------------------------------------- MEMORY
with tab_mem:
    st.subheader("Long-term memory — per-repo decision history")
    st.caption("What this team has approved/rejected per rule, persisted across runs.")
    try:
        with PostgresStore.from_conn_string(URL) as store:
            store.setup()
            rows = []
            for item in store.search(("decisions", REPO)):
                rows.append({"rule": item.key,
                             "approved": item.value.get("approved", 0),
                             "rejected": item.value.get("rejected", 0)})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No decisions recorded yet — approve or reject a fix to build memory.")
    except Exception as e:
        st.error(f"Could not load memory: {e}")


# ---------------------------------------------------------------- EVAL
with tab_eval:
    st.subheader("Evaluation — agentic pipeline vs. naive single-LLM baseline")
    st.caption("Measured on a held-out benchmark of 16 labeled cases (positives, negatives, mixed).")
    df = pd.DataFrame([
        {"approach": "Naive single-LLM baseline", "precision": 0.90, "recall": 1.00, "f1": 0.95},
        {"approach": "PolicyGate agentic pipeline", "precision": 1.00, "recall": 1.00, "f1": 1.00},
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown(
        "- **Pipeline: precision 1.00, recall 1.00** on the 3 enforced defect rules.\n"
        "- **Zero false positives** on clean cases (parameterized queries, validated handlers, batched queries).\n"
        "- The pipeline's edge is **precision** — the focused per-rule specialists avoid the false "
        "positives the single call makes, which is what determines whether a review tool gets trusted."
    )
    st.caption("Reproduce: `python eval/baseline.py`")


# ---------------------------------------------------------------- SCAN
def _detect_only(files: dict) -> list:
    state = {"files": files}
    out = []
    for sp in (security_specialist, perf_specialist):
        out += sp(state).get("violations", [])
    return out


with tab_scan:
    st.subheader("Scan any public repo (detection)")
    st.caption("Points detection at a real third-party repo — shows it generalizes beyond the demo.")
    repo = st.text_input("owner/repo", value="JasonHinds13/hackable")
    if st.button("🔍 Scan", type="primary"):
        try:
            with st.spinner(f"Fetching & scanning {repo}..."):
                all_py = list_python_files(repo)
                cand = fetch_files(repo, all_py[:12])
                relevant = {p: c for p, c in cand.items() if any(h in c for h in SQL_HINTS)}
                files = relevant or dict(list(cand.items())[:3])
                viols = _detect_only(files)
            st.write(f"Scanned {len(files)} file(s): {list(files)}")
            if not viols:
                st.info("No violations of the enforced rules found.")
            else:
                st.success(f"Found {len(viols)} violation(s) in real third-party code")
                st.dataframe(pd.DataFrame([
                    {"rule": v["rule_id"], "file": v["file"],
                     "line": v["line_start"], "severity": v["severity"]}
                    for v in viols
                ]), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Scan failed: {e}")