"""CLI runner: python main.py   (needs OPENAI_API_KEY)"""
import uuid

from langgraph.types import Command

from graph import build_graph


def main() -> None:
    app = build_graph()
    cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}
    print("🛒 AI Shopping Assistant\n")
    payload = {}
    while True:
        result = app.invoke(payload, cfg)
        pending = result.get("__interrupt__")
        if not pending:
            break
        q = pending[0].value
        if isinstance(q, dict):  # recommendation + yes/no question
            print("\n" + q["recommendation"] + "\n")
            q = q["question"]
        payload = Command(resume=input(f"{q}\n> "))
    print("\nThanks for shopping with me. Happy with your purchase! 👋")


if __name__ == "__main__":
    main()
