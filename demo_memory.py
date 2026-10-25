"""Demo: three chats, each with a follow-up question. Run: python demo_memory.py

The memory works per thread_id, so each chat below has its own thread.
"""
from src.graph import run_query

EMPLOYEE_ID = "E1001"

CHATS: list[tuple[str, list[str]]] = [
    ("chat-wfh", ["What is the work from home rule?", "and for interns?"]),
    ("chat-allowance", ["How much is the daily travel allowance in metro cities?", "and for non-metro?"]),
    ("chat-leave", ["How many casual leaves do I get in a year?", "what about interns?"]),
]


def show_turn(question: str, result: dict) -> None:
    """Print what the employee typed, what the system understood, and the answer."""
    print(f"  You typed    : {question}")
    print(f"  Rewritten as : {result['rewritten_question']}")
    print(f"  Route        : {result['route']} | Confidence: {result['confidence']}")
    print(f"  Answer       : {result['answer']}")
    for citation in result["citations"]:
        print(f"  Source       : {citation['source']} | {citation['section']}")
    print()


def main() -> None:
    """Run every chat, one question after the other, in the same thread."""
    print("Starting (the very first question is slow because the models load once)...\n")
    for thread_id, questions in CHATS:
        print("=" * 70)
        print(f"Chat: {thread_id}")
        for question in questions:
            show_turn(question, run_query(question, EMPLOYEE_ID, thread_id))


if __name__ == "__main__":
    main()