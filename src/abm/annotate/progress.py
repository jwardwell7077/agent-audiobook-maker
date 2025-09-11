from __future__ import annotations


class ProgressReporter:
    """Simple progress reporter with rich/tqdm/print fallbacks."""

    def __init__(self, total: int, mode: str = "auto", title: str = "Processing chapters") -> None:
        """Create a progress reporter.

        Args:
            total: Total number of items.
            mode: "auto" | "rich" | "tqdm" | "none".
            title: Display title for rich.
        """
        self.total = total
        self.mode = mode
        self.title = title
        self._count = 0

        self._use_rich = False
        self._use_tqdm = False
        self._rich = None
        self._task_id = None
        self._tqdm = None

        if mode in ("auto", "rich"):
            try:
                from rich.progress import Progress  # type: ignore

                self._rich = Progress()
                self._use_rich = True
            except Exception:
                self._use_rich = False
        if not self._use_rich and mode in ("auto", "tqdm"):
            try:
                from tqdm import tqdm  # type: ignore

                self._tqdm = tqdm(total=total, desc=title)
                self._use_tqdm = True
            except Exception:
                self._use_tqdm = False

    def __enter__(self) -> ProgressReporter:
        if self._use_rich and self._rich is not None:
            self._rich.start()
            self._task_id = self._rich.add_task(self.title, total=self.total)
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._use_rich and self._rich is not None:
            self._rich.stop()
        if self._use_tqdm and self._tqdm is not None:
            self._tqdm.close()

    def advance(self, n: int = 1, text: str | None = None) -> None:
        """Advance progress by n and optionally set a status text."""
        self._count += n
        if self._use_rich and self._rich is not None and self._task_id is not None:
            if text:
                self._rich.update(self._task_id, advance=n, description=f"{self.title} | {text}")
            else:
                self._rich.update(self._task_id, advance=n)
        elif self._use_tqdm and self._tqdm is not None:
            if text:
                self._tqdm.set_postfix_str(text, refresh=True)
            self._tqdm.update(n)
        else:
            # Plain stdout
            if text:
                print(f"[{self._count}/{self.total}] {text}")
            else:
                print(f"[{self._count}/{self.total}]")
