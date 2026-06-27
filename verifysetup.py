import os
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
print("[ok] core imports work")

class S(BaseModel):
    n: int = 0
g = StateGraph(S)
g.add_node("inc", lambda s: {"n": s.n + 1})
g.add_edge(START, "inc")
g.add_edge("inc", END)
g.compile()
print("[ok] StateGraph compiles")

print("\nSETUP OK — ready for Part 1")