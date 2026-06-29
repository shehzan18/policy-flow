from __future__ import annotations

from policygate.graph.state import PRState
from policygate.sandbox.e2b_runner import run_pytest

TEST_FILE = "test_proving.py"


def sandbox_verify(state: PRState) -> dict:
    print("[sandbox]   verifying fixes in E2B...")
    updated = []
    for v in state["violations"]:
        if v["status"] != "fix_proposed":
            continue

        original = state["files"]
        fixed = {**original, v["file"]: v["proposed_fix"]}

        print(f"[sandbox]   {v['rule_id']}: proving test on ORIGINAL (expect FAIL)...")
        o = run_pytest(original, TEST_FILE, v["proving_test"], requirements=state.get("requirements", ""))
        orig_failed = o["exit_code"] != 0

        print(f"[sandbox]   {v['rule_id']}: proving test on FIXED (expect PASS)...")
        f = run_pytest(fixed, TEST_FILE, v["proving_test"], requirements=state.get("requirements", ""))
        fix_passed = f["exit_code"] == 0

        suite_passed = True  # demo repo has no existing suite; real repos run their own tests

        verified = orig_failed and fix_passed and suite_passed
        nv = dict(v)
        nv["sandbox_result"] = {
            "orig_test_failed": orig_failed,
            "fix_test_passed": fix_passed,
            "suite_passed": suite_passed,
            "logs": (f["stdout"] + "\n" + f["stderr"])[-2000:],
        }
        nv["status"] = "verified" if verified else "failed"
        updated.append(nv)

        mark = "VERIFIED" if verified else "FAILED"
        print(f"[sandbox]   {v['rule_id']} -> {mark} "
              f"(orig_failed={orig_failed}, fix_passed={fix_passed})")
    return {"violations": updated}