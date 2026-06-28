from dotenv import load_dotenv
load_dotenv()

from policygate.graph.build import build_graph, _empty_state

app = build_graph()
state = _empty_state(pr_id="1", repo="shehzan18/policy-flow-demo")
final = app.invoke(state)

print("\n--- generated fixes ---")
for v in final["violations"]:
    print(f"\n### {v['rule_id']} @ {v['file']}:{v['line_start']} [{v['status']}]")
    if v["proposed_fix"]:
        print("--- proposed fix ---")
        print(v["proposed_fix"])
        print("--- proving test ---")
        print(v["proving_test"])