"""HR Policy Copilot: chat window.

Run from the project root:  streamlit run app/streamlit_app.py

This file only draws the screen. The thinking is done by run_query() in src/graph.py.
"""
import sys
from pathlib import Path

# Streamlit puts the folder of THIS file on the path, not the project root,
# so we add the root ourselves. Without it, "from src..." would fail.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from src.app_support import (  # noqa: E402
    append_feedback,
    llm_label,
    load_users,
    new_thread_id,
    user_label,
)
from src.graph import HR_EMAIL, run_query, warm_up  # noqa: E402

st.set_page_config(page_title="HR Policy Copilot", page_icon="💬")


@st.cache_resource(show_spinner="Loading the models (only the first time, this can take a minute)...")
def load_models() -> bool:
    """Load the slow parts once for the whole program, not on every rerun."""
    warm_up()
    return True


def start_new_chat() -> None:
    """Forget the shown messages and use a new thread_id (a new conversation memory)."""
    st.session_state.messages = []
    st.session_state.thread_id = new_thread_id()


def init_state() -> None:
    """Create the values we keep between reruns (only the first time)."""
    if "thread_id" not in st.session_state:
        start_new_chat()


def rate_answer(index: int, rating: str) -> None:
    """Button callback: save the rating of answer number `index` to feedback.jsonl."""
    message = st.session_state.messages[index]
    append_feedback(message["question"], message["content"], rating, message["route"])
    message["rating"] = rating


def show_rating(message: dict, index: int) -> None:
    """Thumbs up and thumbs down buttons, or a thank-you after one was clicked."""
    if message["rating"]:
        st.caption(f"Thanks for your feedback ({'👍' if message['rating'] == 'up' else '👎'}).")
        return
    key = f"{st.session_state.thread_id}-{index}"
    up, down, _ = st.columns([1, 1, 6])
    up.button("👍", key=f"up-{key}", on_click=rate_answer, args=(index, "up"))
    down.button("👎", key=f"down-{key}", on_click=rate_answer, args=(index, "down"))


def show_details(message: dict, index: int) -> None:
    """Everything under an assistant answer: HR notice, Sources, latency, thumbs."""
    if message["escalate"]:
        st.warning(f"**Please contact HR** at {HR_EMAIL} to confirm this.")
    with st.expander("Sources"):
        st.caption(f"Route: {message['route']} | Confidence: {message['confidence']}")
        if message["rewritten"] != message["question"]:
            st.caption(f"Searched as: {message['rewritten']}")
        if not message["citations"]:
            st.write("No policy sources for this answer.")
        for citation in message["citations"]:
            st.markdown(f"**{citation['source']}** - {citation['section']}")
            st.markdown(f"> {citation['quote']}")
    st.caption(f"Answered in {message['latency']:.1f} s")
    show_rating(message, index)


def show_message(message: dict, index: int) -> None:
    """Draw one chat bubble (with its details if it is an answer)."""
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            show_details(message, index)


def ask(question: str, employee_id: str) -> None:
    """Send the question to the copilot, then show and store the answer."""
    user_message = {"role": "user", "content": question}
    st.session_state.messages.append(user_message)
    show_message(user_message, len(st.session_state.messages) - 1)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching the HR policies..."):
                result = run_query(question, employee_id, st.session_state.thread_id)
        except Exception as error:  # for example the free AI service is busy (rate limit)
            st.error("Sorry, something went wrong. The free AI service may be busy. "
                     "Please try again in a few seconds.")
            st.caption(f"{type(error).__name__}: {error}")
            st.session_state.messages.pop()  # forget the question that got no answer
            return

    answer = {
        "role": "assistant",
        "content": result["answer"],
        "question": question,
        "rewritten": result["rewritten_question"],
        "route": result["route"],
        "confidence": result["confidence"],
        "citations": result["citations"],
        "escalate": result["escalate_to_hr"],
        "latency": result["latency"]["total_seconds"],
        "rating": None,
    }
    st.session_state.messages.append(answer)
    show_message(answer, len(st.session_state.messages) - 1)


def main() -> None:
    """Draw the whole page. Streamlit runs this again after every click."""
    init_state()
    load_models()
    users = load_users()

    with st.sidebar:
        st.header("HR Policy Copilot")
        employee_id = st.selectbox(
            "Logged-in user",
            options=list(users),
            format_func=lambda employee: user_label(employee, users),
            key="employee_id",
            on_change=start_new_chat,  # a different person must not see the old chat
        )
        st.caption(f"LLM: {llm_label()}")
        st.button("New chat", on_click=start_new_chat)
        st.caption(f"Chat id: {st.session_state.thread_id}")

    st.title("HR Policy Copilot")
    st.caption("Ask about leave, expenses, work from home, IT use and more.")

    for index, message in enumerate(st.session_state.messages):
        show_message(message, index)

    question = st.chat_input("Ask a question about HR policies...")
    if question:
        ask(question, employee_id)


main()