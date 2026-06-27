from dotenv import load_dotenv
load_dotenv()

from policygate.graph.build import build_graph, _empty_state

app = build_graph()
state = _empty_state(pr_id="1", repo="shehzan18/policy-flow-demo")
final = app.invoke(state)

print("\n--- files pulled into state ---")
for path, content in final["files"].items():
    print(f"{path} ({len(content)} chars)")
    print(content)