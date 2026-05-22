import ctypes

from prompt_toolkit import prompt as tk_prompt
from prompt_toolkit.styles import Style
from rich.console import Console

_console = Console()
_PROMPT_STYLE = Style.from_dict({"prompt": "#00c6ff"})


class PermissionGate:
    @staticmethod
    def has_admin() -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @staticmethod
    def ask_initial_permissions() -> None:
        import time
        import sys
        from display.banner import get_theme_color

        theme_col = get_theme_color()
        _console.print()
        _console.print(f"  [bold {theme_col}]System Initialization[/bold {theme_col}]")
        _console.print("  [dim]─────────────────────[/dim]")

        permissions = [
            "Network Adapter & Traffic Analysis",
            "Storage Drive Deep Scan Access",
            "Process Management & Termination",
            "System Registry & Environment Variables",
        ]

        for perm in permissions:
            try:
                raw = tk_prompt(
                    f"  ❯ Grant access to {perm} [y/n]: ",
                    style=_PROMPT_STYLE,
                ).strip().lower()
            except (KeyboardInterrupt, EOFError):
                raw = "n"

            sys.stdout.write("\033[1A\r\033[2K")
            sys.stdout.flush()

            if raw == "y":
                with _console.status(f"  [bold {theme_col}]Initializing {perm}...[/bold {theme_col}]", spinner="dots"):
                    time.sleep(1.2)
                _console.print(f"  [bold green]✓[/bold green] [dim]{perm}[/dim]")
            else:
                with _console.status(f"  [dim]Skipping {perm}...[/dim]", spinner="dots"):
                    time.sleep(0.6)
                _console.print(f"  [bold red]✗[/bold red] [dim]{perm} (Skipped)[/dim]")
            time.sleep(0.3)

        _console.print(f"\n  [bold green]✓[/bold green] [dim]All subsystems online. Ready.[/dim]\n")

    @staticmethod
    def ask_permission(intent: str = "") -> str:
        from display.banner import get_theme_color
        from display.animations import AnimatedMenu

        theme_col = get_theme_color()
        intent_key = (intent or "").upper()

        fix_desc = "Apply automatic fix"
        if intent_key == "NETWORK":
            fix_desc = "Flush DNS & Switch to Google DNS"
        elif intent_key == "STORAGE":
            fix_desc = "Run storage cleanup (Temp & Recycle Bin)"
        elif intent_key == "DEV_ENV":
            fix_desc = "Repair Python environment PATH"
        elif intent_key == "SYSTEM":
            fix_desc = "Terminate high-memory runaway tasks"

        options = [("y", fix_desc, theme_col)]
        if intent_key == "STORAGE":
            options.append(("x", "Find & remove duplicate files", "dim"))
            options.append(("p", "Launch Partition Wizard", "yellow"))
        options += [
            ("d", "Inspect telemetry diagnostic details", "dim"),
            ("t", "Open an automated support ticket", "magenta"),
            ("n", "Skip recommendations / ignore", "dim"),
        ]

        _console.print()
        _console.print(f"  [bold {theme_col}]Recommendation Dashboard[/bold {theme_col}]")
        _console.print("  [dim]────────────────────────[/dim]")

        menu = AnimatedMenu(options)
        choice = menu.run()

        if choice == "y":
            if intent_key == "NETWORK": return "f"
            if intent_key == "STORAGE": return "c"
            if intent_key == "DEV_ENV": return "y"
            if intent_key == "SYSTEM":  return "k"
        return choice
