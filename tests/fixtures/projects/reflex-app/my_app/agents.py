"""Application logic — pure Python, no JavaScript anywhere in the source tree."""

import reflex as rx
from langchain.chains import LLMChain


class State(rx.State):
    """Reflex state. Note: this is pure Python; Reflex transpiles to JS at build."""

    message: str = ""
    response: str = ""

    def send(self) -> None:
        self.response = f"echo: {self.message}"


def chat_component() -> rx.Component:
    return rx.vstack(
        rx.input(value=State.message, on_change=State.set_message),
        rx.button("Send", on_click=State.send),
        rx.text(State.response),
    )
