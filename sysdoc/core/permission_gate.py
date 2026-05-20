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
        from rich.prompt import Confirm
        from display.banner import get_theme_color
        
        theme_col = get_theme_color()
        _console.print()
        _console.print(f"  [bold {theme_col}]System Initialization[/bold {theme_col}]")
        _console.print("  [dim]─────────────────────[/dim]")
        
        permissions = [
            "Network Adapter & Traffic Analysis",
            "Storage Drive Deep Scan Access",
            "Process Management & Termination",
            "System Registry & Environment Variables"
        ]
        
        for perm in permissions:
            ans = Confirm.ask(f"  [bold {theme_col}]❯[/bold {theme_col}] Grant access to {perm}", default=True)
            sys.stdout.write("\033[1A\r\033[2K")
            sys.stdout.flush()
            if ans:
                with _console.status(f"  [bold {theme_col}]Initializing {perm}...[/bold {theme_col}]", spinner="dots"):
                    time.sleep(0.8)
                _console.print(f"  [bold green]✓[/bold green] [dim]{perm}[/dim]")
            else:
                _console.print(f"  [bold red]✗[/bold red] [dim]{perm} (Skipped)[/dim]")
            time.sleep(0.1)
            
        _console.print(f"\n  [bold green]✓[/bold green] [dim]All subsystems online. Ready.[/dim]\n")

    @staticmethod
    def ask_permission(intent: str = "") -> str:
        from display.banner import get_theme_color
        theme_col = get_theme_color()

        intent_key = (intent or "").upper()
        options = []
        
        # Dynamically customize the automatic fix option label
        fix_desc = "Apply automatic fix"
        extra_options = []
        if intent_key == "NETWORK":
            fix_desc = "Flush DNS & Switch to Google DNS [f]"
        elif intent_key == "STORAGE":
            fix_desc = "Run storage cleanup (Temp & Recycle Bin) [c]"
            extra_options.append(f"  [bold {theme_col}]p[/bold {theme_col}] [dim]→[/dim] Launch Partition Wizard")
        elif intent_key == "DEV_ENV":
            fix_desc = "Repair Python environment PATH [y]"
        elif intent_key == "SYSTEM":
            fix_desc = "Terminate high-memory runaway tasks [k]"

        options.append(f"  [bold {theme_col}]y[/bold {theme_col}] [dim]→[/dim] {fix_desc}")
        options.extend(extra_options)
        options.append(f"  [bold {theme_col}]d[/bold {theme_col}] [dim]→[/dim] Inspect telemetry diagnostic details")
        options.append(f"  [bold {theme_col}]t[/bold {theme_col}] [dim]→[/dim] Open an automated support ticket")
        options.append(f"  [bold {theme_col}]n[/bold {theme_col}] [dim]→[/dim] Skip recommendations / ignore")

        _console.print()
        _console.print(f"  [bold {theme_col}]Recommendation Dashboard[/bold {theme_col}]")
        _console.print("  [dim]────────────────────────[/dim]")
        for opt in options:
            _console.print(f"  {opt}")
        _console.print()

        valid_choices = {"y", "d", "p", "t", "n", "c", "v", "k", "r", "f"}
        attempts = 0
        while attempts < 3:
            try:
                choice = tk_prompt("  ❯ Select action: ", style=_PROMPT_STYLE).strip().lower()
            except (KeyboardInterrupt, EOFError):
                return "n"
            if choice in valid_choices:
                # If they pressed 'y' (default fix), map to actual shortcut key for backend if intent is active
                if choice == "y":
                    if intent_key == "NETWORK": return "f"
                    if intent_key == "STORAGE": return "c"
                    if intent_key == "DEV_ENV": return "y"
                    if intent_key == "SYSTEM": return "k"
                return choice
            attempts += 1
            _console.print("  [bold red]✗[/bold red] [dim]Invalid choice. Select a mapped action shortcut.[/dim]")
        return "n"
