import os
import sys

from dotenv import load_dotenv
load_dotenv()

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command

from policygate.graph.build import build_graph, _empty_state

REPO = "shehzan18/policy-flow-demo"


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    pr_id = sys.argv[2] if len(sys.argv) > 2 else "1"
    url = os.environ["DATABASE_URL"]

    with PostgresSaver.from_conn_string(url) as saver:
        saver.setup()  # idempotent: creates checkpoint tables on first run
        app = build_graph(checkpointer=saver)
        cfg = {"configurable": {"thread_id": f"pr-{pr_id}"}}

        if mode == "run":
            try:
                saver.delete_thread(f"pr-{pr_id}")  # clean slate for a repeatable run
            except Exception:
                pass
            result = app.invoke(_empty_state(pr_id=pr_id, repo=REPO), config=cfg)
        elif mode in ("approve", "reject"):
            result = app.invoke(Command(resume=mode), config=cfg)
        else:
            print("usage: python review.py [run|approve|reject] <pr_id>")
            return

        if "__interrupt__" in result:
            payload = result["__interrupt__"][0].value
            print("\n=== FROZEN — awaiting human approval ===")
            print(f"PR #{payload['pr_id']} has {len(payload['fixes'])} verified fix(es):")
            for f in payload["fixes"]:
                print(f"  - {f['rule_id']} in {f['file']}")
            print(f"\nApprove:  python review.py approve {pr_id}")
            print(f"Reject:   python review.py reject {pr_id}")
        else:
            print("\n=== DONE ===")
            print("human decision:", result.get("human_decision"))
            for v in result["violations"]:
                print(f"  - {v['rule_id']} -> {v['status']}")


if __name__ == "__main__":
    main()