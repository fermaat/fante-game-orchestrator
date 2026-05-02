"""Stdin/stdout adapters for terminal play."""


class StdinInput:
    """InputPort backed by `input()`. Returns None on EOF or quit word."""

    def __init__(
        self,
        prompt: str = "> ",
        quit_words: tuple[str, ...] = ("quit", "exit", "salir"),
    ) -> None:
        self._prompt = prompt
        self._quit_words = quit_words

    def read(self) -> str | None:
        try:
            line = input(self._prompt).strip()
        except EOFError:
            return None
        if line.lower() in self._quit_words:
            return None
        return line


class StdoutOutput:
    """OutputPort that prints to stdout."""

    def emit(self, text: str) -> None:
        print(text)
