"""HR Policy Copilot: chat window.

Run from the project root:  streamlit run app/streamlit_app.py

This file only draws the screen. The thinking is done by run_query() in src/graph.py.
The look uses Streamlit's own default theme (light or dark, chosen in the three-dot menu).
One small CSS block (HIDE_EXTRAS_CSS) hides the Stop button, Deploy and the footer text.
"""
import sys
from pathlib import Path

# Streamlit puts the folder of THIS file on the path, not the project root,
# so we add the root ourselves. Without it, "from src..." would fail.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from src.app_support import (  # noqa: E402
    append_feedback,
    llm_label,
    load_users,
    new_thread_id,
    user_label,
)
from src.graph import HR_EMAIL, run_query, warm_up  # noqa: E402
from src.logging_utils import setup_logging  # noqa: E402

FAVICON = ROOT / "assets" / "favicon.png"  # made by: python -m src.make_favicon
AVATARS = {"user": ROOT / "assets" / "avatar_user.png", "assistant": ROOT / "assets" / "avatar_assistant.png"}
RATINGS = {1: "up", 0: "down"}  # what st.feedback("thumbs") returns: 1 is thumbs up, 0 is thumbs down

# Streamlit has no setting for these items, so CSS hides them. The three-dot menu (light and dark mode) stays.
# These names are Streamlit's own test ids and can change in a new version. Delete this block to undo it.
HIDE_EXTRAS_CSS = """
<style>
[data-testid="stStatusWidget"], [data-testid="stDeployButton"], [data-testid="stDecoration"],
footer { display: none !important; }
</style>
"""

st.set_page_config(
    page_title="HR Policy Copilot",
    page_icon=str(FAVICON) if FAVICON.exists() else None,  # no icon (not an emoji) if the file is missing
    layout="wide",
)


def avatar_for(role: str) -> str | None:
    """Path of the letter avatar for this role, or None (Streamlit's own icon) if the file is missing."""
    path = AVATARS[role]
    return str(path) if path.exists() else None


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


def rate_answer(index: int, widget_key: str) -> None:
    """Callback of the thumbs widget: save the rating of answer number `index` once."""
    rating = RATINGS.get(st.session_state.get(widget_key))
    message = st.session_state.messages[index]
    if rating is None or message["rating"]:
        return
    append_feedback(message["question"], message["content"], rating, message["route"])
    message["rating"] = rating


def show_rating(message: dict, index: int) -> None:
    """Thumbs up and thumbs down (built-in icons). They lock after one click."""
    key = f"feedback-{st.session_state.thread_id}-{index}"
    st.feedback(
        "thumbs",
        key=key,
        disabled=bool(message["rating"]),
        on_change=rate_answer,
        args=(index, key),
    )
    if message["rating"]:
        st.caption("Thank you for your feedback.")


def show_details(message: dict, index: int) -> None:
    """Everything under an assistant answer: HR notice, Sources, small info line, thumbs."""
    if message["escalate"]:
        st.warning(f"Please contact HR at {HR_EMAIL}")
    with st.expander("Sources"):
        if message["rewritten"] != message["question"]:
            st.caption(f"Searched as: {message['rewritten']}")
        if not message["citations"]:
            st.write("No policy sources for this answer.")
        for citation in message["citations"]:
            st.markdown(f"**{citation['source']}** - {citation['section']}")
            st.markdown(f"> {citation['quote']}")
    st.caption(
        f"Route: {message['route']} | Confidence: {message['confidence']} | "
        f"Answered in {message['latency']:.1f} s"
    )
    show_rating(message, index)


def show_message(message: dict, index: int) -> None:
    """Draw one chat bubble (with its details if it is an answer)."""
    with st.chat_message(message["role"], avatar=avatar_for(message["role"])):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            show_details(message, index)


def ask(question: str, employee_id: str) -> None:
    """Send the question to the copilot, then show and store the answer."""
    user_message = {"role": "user", "content": question}
    st.session_state.messages.append(user_message)
    show_message(user_message, len(st.session_state.messages) - 1)

    with st.chat_message("assistant", avatar=avatar_for("assistant")):
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
    setup_logging()
    init_state()
    load_models()
    users = load_users()
    st.markdown(HIDE_EXTRAS_CSS, unsafe_allow_html=True)

    with st.sidebar:
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
    st.caption("Answers come only from the official policy documents.")

    for index, message in enumerate(st.session_state.messages):
        show_message(message, index)

    question = st.chat_input("Ask a question about HR policies...")
    if question:
        ask(question, employee_id)


main()