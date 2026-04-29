"""Interactive TUI for asking questions about the analyzed repository."""

from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown

from app.chat import ChatSession


class ChatMessage(Markdown):
    """A single chat message displayed as Markdown."""


class SynaptixChat(App):
    """TUI chat interface for querying the analyzed codebase."""

    THEME = "textual-light"

    CSS = """
    Screen { background: #ffffff; }
    #chat-view { overflow-y: auto; padding: 1 2; background: #ffffff; }
    .user-msg { background: #e8f0fe; color: #1a1a1a; margin: 1 0; padding: 1 2; }
    .assistant-msg { background: #f5f5f5; color: #1a1a1a; margin: 1 0; padding: 1 2; }
    .trace-msg { background: #fff8e1; color: #6d4c00; margin: 0 0; padding: 1 2; }
    #prompt-input { dock: bottom; margin: 0 2 1 2; }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self, repo_path: str) -> None:
        super().__init__()
        self.repo_path = repo_path
        self.session: ChatSession | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield VerticalScroll(id="chat-view")
        yield Input(placeholder="Ask about the codebase… (try /find, /explain, /trace)", id="prompt-input")
        yield Footer()

    def on_mount(self) -> None:
        self.session = ChatSession(self.repo_path)
        status = (
            f"Connected to index ({self.session.collection.count()} symbols)"
            if self.session.collection
            else "No index found — run synaptix --path first"
        )
        self.sub_title = f"{self.repo_path}  •  {status}"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        question = event.value.strip()
        if not question:
            return
        event.input.clear()
        self._ask(question)

    @work(thread=True)
    def _ask(self, question: str) -> None:
        assert self.session is not None
        chat_view = self.query_one("#chat-view")

        user_widget = ChatMessage(f"**You:** {question}")
        user_widget.add_class("user-msg")
        self.call_from_thread(chat_view.mount, user_widget)

        assistant_widget = ChatMessage("**Synaptix:** ")
        assistant_widget.add_class("assistant-msg")
        trace_widget: ChatMessage | None = None
        full = ""

        for etype, content in self.session.handle(question):
            if etype == "trace":
                trace_widget = ChatMessage("**🔍 Retrieval trace:**\n" + content)
                trace_widget.add_class("trace-msg")
                self.call_from_thread(chat_view.mount, trace_widget)
                self.call_from_thread(chat_view.mount, assistant_widget)
            elif etype == "token":
                if trace_widget is None and assistant_widget.parent is None:
                    self.call_from_thread(chat_view.mount, assistant_widget)
                full += content
                self.call_from_thread(assistant_widget.update, f"**Synaptix:** {full}")
            elif etype == "error":
                if assistant_widget.parent is None:
                    self.call_from_thread(chat_view.mount, assistant_widget)
                self.call_from_thread(
                    assistant_widget.update, f"**Synaptix:** Error: {content}",
                )

        self.call_from_thread(chat_view.scroll_end)


def run_tui(repo_path: str) -> None:
    """Launch the interactive TUI."""
    app = SynaptixChat(repo_path)
    app.run()
