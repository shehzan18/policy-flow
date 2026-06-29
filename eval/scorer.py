import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import json
from collections import defaultdict

from policygate.graph.nodes.specialists import (
    security_specialist, perf_specialist,
)

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "benchmark")

# the rules PolicyGate actually enforces / auto-fixes (coverage excluded by design)
ENFORCED_RULES = ("SEC-SQLI", "SEC-VALIDATION", "PERF-NPLUSONE")


def _load_cases():
    labels = json.load(open(os.path.join(BENCH, "labels.json")))
    cases = []
    for cid, meta in labels.items():
        files = {}
        for fn in meta["files"]:
            with open(os.path.join(BENCH, cid, fn), encoding="utf-8") as f:
                files[fn] = f.read()
        # only score the enforced rules (drop any TEST-COVERAGE labels)
        expected = {(r, f) for r, f in meta["expected"] if r in ENFORCED_RULES}
        cases.append((cid, files, expected))
    return cases


def _detect_all(files: dict) -> set:
    """Run the enforced-rule specialists on a case, return set of (rule_id, file)."""
    state = {"files": files}
    found = set()
    for specialist in (security_specialist, perf_specialist):  # coverage excluded by design
        out = specialist(state)
        for v in out.get("violations", []):
            if v["rule_id"] in ENFORCED_RULES:
                found.add((v["rule_id"], v["file"]))
    return found


def score(detect_fn=_detect_all, verbose=True):
    cases = _load_cases()
    tp = fp = fn = 0
    per_rule = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    clean_false_positives = 0

    for cid, files, expected in cases:
        found = detect_fn(files)
        case_tp = found & expected
        case_fp = found - expected
        case_fn = expected - found
        tp += len(case_tp)
        fp += len(case_fp)
        fn += len(case_fn)
        for r, _ in case_tp:
            per_rule[r]["tp"] += 1
        for r, _ in case_fp:
            per_rule[r]["fp"] += 1
        for r, _ in case_fn:
            per_rule[r]["fn"] += 1
        if not expected and found:
            clean_false_positives += 1
        if verbose:
            mark = "ok " if not case_fp and not case_fn else "XX "
            print(f"  {mark}{cid:28s} found={sorted(r for r, _ in found)} "
                  f"expected={sorted(r for r, _ in expected)}")

    def pr(tp, fp, fn):
        p = tp / (tp + fp) if (tp + fp) else 1.0
        r = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        return p, r, f1

    p, r, f1 = pr(tp, fp, fn)
    if verbose:
        print("\n  per-rule:")
        for rule in ENFORCED_RULES:
            s = per_rule[rule]
            rp, rr, _ = pr(s["tp"], s["fp"], s["fn"])
            print(f"    {rule:16s} precision={rp:.2f} recall={rr:.2f} "
                  f"(tp={s['tp']} fp={s['fp']} fn={s['fn']})")
        print(f"\n  OVERALL  precision={p:.2f}  recall={r:.2f}  f1={f1:.2f}")
        print(f"  clean cases with false positives: {clean_false_positives}/"
              f"{sum(1 for _, _, e in cases if not e)}")
    return {"precision": p, "recall": r, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


if __name__ == "__main__":
    print("=== PolicyGate detection eval ===")
    score()