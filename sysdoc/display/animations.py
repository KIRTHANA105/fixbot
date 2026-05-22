import sys
import time
import threading
import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# ANSI colour codes used by BlinkingCursor (avoids pulling Rich into a bg thread)
_ANSI_COLORS = {
    "white":   "\033[97m",
    "cyan":    "\033[96m",
    "yellow":  "\033[93m",
    "magenta": "\033[95m",
    "green":   "\033[92m",
    "dim":     "\033[2m",
}
_ANSI_RESET = "\033[0m"


class BlinkingCursor:
    """
    Blinks a ▌ symbol on a background thread.
    Appears in-line right after whatever was last printed.
    Call .start() to begin blinking, .stop() to erase and join the thread.
    """

    def __init__(self, color: str = "white", interval: float = 0.45):
        self._ansi = _ANSI_COLORS.get(color, "")
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._blink, daemon=True)
        self._thread.start()

    def _blink(self) -> None:
        shown = False
        while not self._stop_event.is_set():
            if shown:
                sys.stdout.write("\b \b")   # erase the cursor character
            else:
                sys.stdout.write(f"{self._ansi}▌{_ANSI_RESET}")
            sys.stdout.flush()
            shown = not shown
            self._stop_event.wait(self._interval)
        # guarantee cursor is erased when stopped
        if shown:
            sys.stdout.write("\b \b")
            sys.stdout.flush()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join()


def typewriter(text: str, color: str = "white", delay: float = 0.022) -> None:
    ansi = _ANSI_COLORS.get(color, "")
    for char in text:
        sys.stdout.write(f"{ansi}{char}{_ANSI_RESET}")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()


def typewriter_stream(chunks, color: str = "white", delay: float = 0.013) -> str:
    """
    Print each streaming chunk character by character for a typewriter effect.
    Blinks a cursor while waiting for the first chunk.
    Returns the full assembled reply string.
    """
    full = ""
    ansi = _ANSI_COLORS.get(color, "")
    cursor = BlinkingCursor(color=color)
    cursor.start()
    first = True
    for chunk in chunks:
        if first:
            cursor.stop()       # erase cursor before first character appears
            first = False
        for char in chunk:
            sys.stdout.write(f"{ansi}{char}{_ANSI_RESET}")
            sys.stdout.flush()
            time.sleep(delay)
        full += chunk
    if first:                   # generator was empty
        cursor.stop()
    sys.stdout.write("\n")
    sys.stdout.flush()
    return full


class ScrollingLog:
    """Rolling window of N lines rendered inside a Rich panel."""

    def __init__(self, max_lines: int = 8, title: str = "execution log"):
        self.max_lines = max_lines
        self.title = title
        self.lines: list[tuple[str, str]] = []
        self._drawn = False

    def add(self, text: str, style: str = "white", prefix: str = "") -> None:
        full = f"{prefix}{text}" if prefix else text
        self.lines.append((full, style))
        if len(self.lines) > self.max_lines:
            self.lines.pop(0)
        self._render()

    def _render(self) -> None:
        if self._drawn:
            sys.stdout.write(f"\033[{self.max_lines + 2}A")
            sys.stdout.flush()

        panel_text = Text()
        for text, style in self.lines:
            panel_text.append(text + "\n", style=style)
        for _ in range(self.max_lines - len(self.lines)):
            panel_text.append("\n")

        console.print(Panel(
            panel_text,
            title=f"[dim]{self.title}[/dim]",
            border_style="dim",
            padding=(0, 1),
        ))
        self._drawn = True

    def clear(self) -> None:
        self.lines = []
        self._drawn = False


def log_step(text: str, style: str = "dim", delay: float = 0.0) -> None:
    console.print(f"  [dim]→[/dim] [{style}]{text}[/{style}]")
    if delay:
        time.sleep(delay)


def log_ok(text: str) -> None:
    console.print(f"  [green][✓][/green] {text}")


def log_warn(text: str) -> None:
    console.print(f"  [yellow][!][/yellow] {text}")


def log_err(text: str) -> None:
    console.print(f"  [red][ERR][/red] {text}")


def log_cmd(cmd: str) -> None:
    console.print(f"  [dim]running:[/dim] [white]{cmd}[/white]")


class WgetBar:
    """
    wget-style single-line progress bar for install / update operations.

    Runs the command in a background thread; animates the bar on the
    calling thread.  The bar snaps to 100 % when the process exits.

    Usage:
        bar = WgetBar("discord", color="cyan")
        returncode, output = bar.run(["winget", "install", "--id", "Discord.Discord"])
        if returncode != 0:
            print(output)   # show captured stderr on failure
    """

    _BAR_WIDTH = 33
    _FILL      = "█"
    _EMPTY     = "░"
    _SPEEDS    = [
        "1.2 MB/s", "2.7 MB/s", "3.4 MB/s",
        "1.9 MB/s", "4.1 MB/s", "2.2 MB/s", "3.8 MB/s",
    ]

    def __init__(self, label: str, color: str = "cyan"):
        self._label = label[:24]
        self._ansi  = _ANSI_COLORS.get(color, "\033[96m")

    # ── public ────────────────────────────────────────────────────────────

    def run(self, cmd_list: list) -> tuple[int, str]:
        """Execute cmd_list in a thread; return (returncode, captured_output)."""
        returncode_box: list[int] = [1]
        output_box:     list[str] = [""]

        def _worker() -> None:
            try:
                proc = subprocess.run(
                    cmd_list,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                returncode_box[0] = proc.returncode
                output_box[0]     = proc.stdout + proc.stderr
            except Exception as exc:
                returncode_box[0] = 1
                output_box[0]     = str(exc)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        self._animate(thread, returncode_box)

        return returncode_box[0], output_box[0]

    # ── internals ─────────────────────────────────────────────────────────

    def _animate(self, thread: threading.Thread, returncode_box: list) -> None:
        start = time.time()
        pct   = 0.0
        si    = 0
        first = True

        while thread.is_alive():
            elapsed = time.time() - start
            # Asymptotic curve: fast rise → slows → caps at 95 % until done
            target = min(95.0, 100.0 * (1.0 - 1.0 / (1.0 + elapsed * 0.45)))
            pct   += (target - pct) * 0.35
            self._draw(pct, self._SPEEDS[si % len(self._SPEEDS)], overwrite=not first)
            first  = False
            si    += 1
            thread.join(timeout=0.22)   # doubles as sleep

        # Show green "done" or red "failed" based on real exit code
        status = "done" if returncode_box[0] == 0 else "failed"
        self._draw(100.0, status, overwrite=not first)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def _draw(self, pct: float, speed: str, *, overwrite: bool) -> None:
        filled = int(self._BAR_WIDTH * pct / 100)
        empty  = self._BAR_WIDTH - filled
        bar    = self._FILL * filled + self._EMPTY * empty

        label_col = f"\033[97m{self._label:<24}\033[0m"
        bar_col   = f"\033[2m[\033[0m{self._ansi}{bar}\033[0m\033[2m]\033[0m"
        pct_col   = f"\033[1m{pct:5.1f}%\033[0m"

        if speed == "done":
            spd_col = f"\033[32m{'done':<10}\033[0m"     # green
        elif speed == "failed":
            spd_col = f"\033[31m{'failed':<10}\033[0m"   # red
        else:
            spd_col = f"\033[2m{speed:<10}\033[0m"       # dim

        line = f"  {label_col}  {bar_col}  {pct_col}  {spd_col}"

        if overwrite:
            sys.stdout.write("\r")
        sys.stdout.write(line)
        sys.stdout.flush()


class AnimatedMenu:
    """
    Arrow-key navigable option list.
    ↑ / ↓ to move, Enter to confirm, Esc / Ctrl-C cancels (returns last option's key).
    Falls back to typed input on non-Windows platforms.
    """

    def __init__(self, options: list[tuple[str, str, str]]):
        self.options = options      # [(key, description, color), ...]
        self.selected = 0
        self._drawn = False

    # total lines the rendered block occupies:
    # 1 blank + N options + 1 blank + 1 hint = N + 3
    @property
    def _block_lines(self) -> int:
        return len(self.options) + 3

    def _render(self) -> None:
        if self._drawn:
            sys.stdout.write(f"\033[{self._block_lines}A\033[J")
            sys.stdout.flush()

        console.print()
        for i, (key, desc, color) in enumerate(self.options):
            if i == self.selected:
                console.print(f"  [bold {color}]▶  [{key}]  {desc}[/bold {color}]")
            else:
                console.print(f"  [dim]   [{key}]  {desc}[/dim]")
        console.print()
        console.print("  [dim]↑ ↓  move    Enter  select[/dim]")
        self._drawn = True

    def run(self, prompt_func=None) -> str:
        self.selected = 0
        self._render()
        try:
            import msvcrt
            return self._run_keys(msvcrt)
        except ImportError:
            return self._run_text(prompt_func)

    # ── keyboard navigation (Windows) ─────────────────────────────────────

    def _run_keys(self, msvcrt) -> str:
        while True:
            ch = msvcrt.getch()
            if ch in (b'\xe0', b'\x00'):        # extended-key prefix
                arrow = msvcrt.getch()
                if arrow == b'H':               # ↑
                    self.selected = (self.selected - 1) % len(self.options)
                    self._render()
                elif arrow == b'P':             # ↓
                    self.selected = (self.selected + 1) % len(self.options)
                    self._render()
            elif ch == b'\r':                   # Enter
                console.print()
                return self.options[self.selected][0]
            elif ch in (b'\x03', b'\x1b'):      # Ctrl-C / Esc → pick last option
                console.print()
                return self.options[-1][0]

    # ── typed fallback (non-Windows) ──────────────────────────────────────

    def _run_text(self, prompt_func) -> str:
        valid = {opt[0] for opt in self.options}
        if prompt_func is None:
            import builtins
            get_input = lambda: builtins.input("  choice → ").strip()
        else:
            get_input = prompt_func

        while True:
            try:
                choice = get_input().strip()
            except (KeyboardInterrupt, EOFError):
                return self.options[-1][0]
            if not choice:
                continue
            if choice in valid:
                return choice
            console.print(f"  [dim]type one of: {', '.join(sorted(valid))}[/dim]")


class MultiSelectMenu:
    """
    Arrow-key + Space multi-select list for update selection.

    ↑ ↓  navigate     Space  toggle selection
    A    select all   Enter  confirm   Esc / Ctrl-C  cancel

    items: list of dicts with keys: name, from, to, source
    Returns list of selected item dicts (empty list = cancelled / none chosen).
    """

    _W_NAME    = 26
    _W_FROM    = 11
    _W_TO      = 11
    _W_SRC     =  7
    _PAGE_SIZE = 14   # max items shown at once — keeps the block short enough to redraw without jumping

    def __init__(self, items: list[dict], color: str = "cyan"):
        self.items    = items
        self.color    = color
        self.cursor   = 0
        self.selected: set[int] = set()
        self._drawn   = False

    @property
    def _block_lines(self) -> int:
        # header + separator + visible items + blank + hint
        return min(len(self.items), self._PAGE_SIZE) + 4

    def _viewport(self) -> tuple[int, int]:
        """Sliding window that keeps the cursor centred in the visible region."""
        n  = len(self.items)
        ps = min(n, self._PAGE_SIZE)
        start = max(0, min(self.cursor - ps // 2, n - ps))
        return start, start + ps

    def _render(self) -> None:
        col   = _ANSI_COLORS.get(self.color, "\033[96m")
        reset = _ANSI_RESET
        dim   = "\033[2m"
        bold  = "\033[1m"
        white = "\033[97m"

        if self._drawn:
            sys.stdout.write(f"\033[{self._block_lines}A\033[J")
            sys.stdout.flush()

        start, end = self._viewport()
        total = len(self.items)
        pos   = f"  {start + 1}-{end}/{total}" if total > self._PAGE_SIZE else ""

        # Header + separator (pure sys.stdout — no Rich, so line count is exact)
        sys.stdout.write(
            f"  {dim}{'App':<{self._W_NAME + 5}} "
            f"{'Current':<{self._W_FROM}}   "
            f"{'Available':<{self._W_TO}} Source{reset}\n"
        )
        sys.stdout.write(f"  {dim}{'─' * 64}{reset}\n")

        for i in range(start, end):
            item      = self.items[i]
            checked   = "✓" if i in self.selected else " "   # ✓ or space
            at_cursor = i == self.cursor
            is_sel    = i in self.selected

            name = item.get("name",   "?")[:self._W_NAME]
            frm  = item.get("from",   "?")[:self._W_FROM]
            to   = item.get("to",     "?")[:self._W_TO]
            src  = item.get("source", "")[:self._W_SRC]

            row = (
                f"[{checked}] {name:<{self._W_NAME}}  "
                f"{frm:<{self._W_FROM}} → {to:<{self._W_TO}} {src}"
            )

            if at_cursor and is_sel:
                sys.stdout.write(f"  {bold}{col}▶ {row}{reset}\n")
            elif at_cursor:
                sys.stdout.write(f"  {col}▶ {row}{reset}\n")
            elif is_sel:
                sys.stdout.write(f"  {bold}{white}  {row}{reset}\n")
            else:
                sys.stdout.write(f"  {dim}  {row}{reset}\n")

        n_sel    = len(self.selected)
        sel_note = f"  ({n_sel} selected)" if n_sel else ""
        sys.stdout.write(
            f"\n  {dim}↑ ↓ move   Space select   A all   "
            f"Enter confirm   Esc cancel{sel_note}{pos}{reset}\n"
        )
        sys.stdout.flush()
        self._drawn = True

    # ── public entry ──────────────────────────────────────────────────────

    def run(self) -> list[dict]:
        self.cursor   = 0
        self.selected = set()
        self._drawn   = False
        self._render()
        try:
            import msvcrt
            return self._run_keys(msvcrt)
        except ImportError:
            return self._run_text()

    # ── keyboard (Windows) ────────────────────────────────────────────────

    def _run_keys(self, msvcrt) -> list[dict]:
        while True:
            ch = msvcrt.getch()
            if ch in (b'\xe0', b'\x00'):
                arrow = msvcrt.getch()
                if arrow == b'H':           # ↑
                    self.cursor = (self.cursor - 1) % len(self.items)
                    self._render()
                elif arrow == b'P':         # ↓
                    self.cursor = (self.cursor + 1) % len(self.items)
                    self._render()
            elif ch == b' ':               # Space — toggle
                if self.cursor in self.selected:
                    self.selected.discard(self.cursor)
                else:
                    self.selected.add(self.cursor)
                self._render()
            elif ch in (b'a', b'A'):       # A — select / deselect all
                if len(self.selected) == len(self.items):
                    self.selected.clear()
                else:
                    self.selected = set(range(len(self.items)))
                self._render()
            elif ch == b'\r':              # Enter — confirm
                sys.stdout.write("\n")
                sys.stdout.flush()
                return [self.items[i] for i in sorted(self.selected)]
            elif ch in (b'\x03', b'\x1b'): # Ctrl-C / Esc — cancel
                sys.stdout.write("\n")
                sys.stdout.flush()
                return []

    # ── typed fallback (non-Windows) ──────────────────────────────────────

    def _run_text(self) -> list[dict]:
        sys.stdout.write("  Enter numbers (e.g. 1,3) or 'all', or Enter to cancel:\n")
        sys.stdout.flush()
        while True:
            try:
                raw = input("  ❯ ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                return []
            if not raw:
                return []
            if raw == "all":
                return list(self.items)
            try:
                idxs = [int(x.strip()) - 1 for x in raw.split(",")]
                return [self.items[i] for i in idxs if 0 <= i < len(self.items)]
            except ValueError:
                sys.stdout.write("  Enter numbers like 1,3 or 'all'\n")
                sys.stdout.flush()
