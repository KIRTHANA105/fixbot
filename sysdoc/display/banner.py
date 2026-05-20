from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

import time
import sys
from rich.prompt import Prompt
import os

THEME_YELLOW = """[yellow]╔════════════════════════════════════════════════════════════════════════════════════╗[/yellow]
[yellow]║[/yellow][gold1]  ★        ☽        ★                                                               [/gold1][yellow]║[/yellow]
[yellow]║[/yellow][gold1]          ·                                         ·                               [/gold1][yellow]║[/yellow]
[yellow]║[/yellow][gold1]                  ✦                      ★                                          [/gold1][yellow]║[/yellow]
[yellow]║[/yellow]                                                                                    [yellow]║[/yellow]
[yellow]║[/yellow]  [#ffff55]███████[/#ffff55][#d4af37]╗[/#d4af37] [#ffff55]██████[/#ffff55][#d4af37]╗[/#d4af37] [#ffff55]████████[/#ffff55][#d4af37]╗[/#d4af37]     [bright_yellow]★[/bright_yellow]  [bold yellow]AI SYSTEM SUPPORT[/bold yellow]  [bright_yellow]☽[/bright_yellow]                            [yellow]║[/yellow]
[yellow]║[/yellow]  [#ffea00]██[/#ffea00][#d4af37]╔════╝[/#d4af37] [#ffea00]██[/#ffea00][#d4af37]╔══[/#d4af37][#ffea00]██[/#ffea00][#d4af37]╗╚══[/#d4af37][#ffea00]██[/#ffea00][#d4af37]╔══╝[/#d4af37]                                                        [yellow]║[/yellow]
[yellow]║[/yellow]  [#ffcc00]█████[/#ffcc00][#d4af37]╗[/#d4af37]   [#ffcc00]██████[/#ffcc00][#d4af37]╔╝[/#d4af37]   [#ffcc00]██[/#ffcc00][#d4af37]║[/#d4af37]        [dim]•[/dim] [bright_white]network[/bright_white]        [dim]•[/dim] [bright_white]diagnostics[/bright_white]                     [yellow]║[/yellow]
[yellow]║[/yellow]  [#ffa600]██[/#ffa600][#d4af37]╔══╝[/#d4af37]   [#ffa600]██[/#ffa600][#d4af37]╔══[/#d4af37][#ffa600]██[/#ffa600][#d4af37]╗[/#d4af37]   [#ffa600]██[/#ffa600][#d4af37]║[/#d4af37]        [dim]•[/dim] [bright_white]installer[/bright_white]      [dim]•[/dim] [bright_white]storage[/bright_white]                         [yellow]║[/yellow]
[yellow]║[/yellow]  [#ff8000]██[/#ff8000][#d4af37]║[/#d4af37]      [#ff8000]██████[/#ff8000][#d4af37]╔╝[/#d4af37]   [#ff8000]██[/#ff8000][#d4af37]║[/#d4af37]        [dim]•[/dim] [bright_white]dev-env[/bright_white]        [dim]•[/dim] [bright_white]monitoring[/bright_white]                      [yellow]║[/yellow]
[yellow]║[/yellow]  [#d4af37]╚═╝[/#d4af37]      [#d4af37]╚═════╝[/#d4af37]    [#d4af37]╚═╝[/#d4af37]                                                           [yellow]║[/yellow]
[yellow]║[/yellow]                                                                                    [yellow]║[/yellow]
[yellow]║[/yellow]        [bold gold1]FIXBOT TERMINAL[/bold gold1]        [dim]>[/dim] [italic bright_white]awaiting intelligent command...[/italic bright_white]                    [yellow]║[/yellow]
[yellow]║[/yellow]                                                                                    [yellow]║[/yellow]
[yellow]║[/yellow][gold1]                   ✦                               ★                                [/gold1][yellow]║[/yellow]
[yellow]║[/yellow][gold1]                                                                                    [/gold1][yellow]║[/yellow]
[yellow]║[/yellow][gold1]          ★                                             ☽                           [/gold1][yellow]║[/yellow]
[yellow]║[/yellow][gold1]                      ·                     ✦                                       [/gold1][yellow]║[/yellow]
[yellow]╚════════════════════════════════════════════════════════════════════════════════════╝[/yellow]"""

THEME_PURPLE = """[blue]╔════════════════════════════════════════════════════════════════════════════════════╗[/blue]
[blue]║[/blue][cyan]  ★        ☽        ★                                                               [/cyan][blue]║[/blue]
[blue]║[/blue][cyan]          ·                                         ·                               [/cyan][blue]║[/blue]
[blue]║[/blue][cyan]                  ✦                      ★                                          [/cyan][blue]║[/blue]
[blue]║[/blue]                                                                                    [blue]║[/blue]
[blue]║[/blue]  [#d484ff]███████[/#d484ff][cyan]╗[/cyan] [#d484ff]██████[/#d484ff][cyan]╗[/cyan] [#d484ff]████████[/#d484ff][cyan]╗[/cyan]     [yellow]★[/yellow]  [bold white]AI SYSTEM SUPPORT[/bold white]  [yellow]☽[/yellow]                            [blue]║[/blue]
[blue]║[/blue]  [#c562ff]██[/#c562ff][cyan]╔════╝[/cyan] [#c562ff]██[/#c562ff][cyan]╔══[/cyan][#c562ff]██[/#c562ff][cyan]╗╚══[/cyan][#c562ff]██[/#c562ff][cyan]╔══╝[/cyan]                                                        [blue]║[/blue]
[blue]║[/blue]  [#b53dff]█████[/#b53dff][cyan]╗[/cyan]   [#b53dff]██████[/#b53dff][cyan]╔╝[/cyan]   [#b53dff]██[/#b53dff][cyan]║[/cyan]        [dim]•[/dim] [white]network[/white]        [dim]•[/dim] [white]diagnostics[/white]                     [blue]║[/blue]
[blue]║[/blue]  [#a115ff]██[/#a115ff][cyan]╔══╝[/cyan]   [#a115ff]██[/#a115ff][cyan]╔══[/cyan][#a115ff]██[/#a115ff][cyan]╗[/cyan]   [#a115ff]██[/#a115ff][cyan]║[/cyan]        [dim]•[/dim] [white]installer[/white]      [dim]•[/dim] [white]storage[/white]                         [blue]║[/blue]
[blue]║[/blue]  [#8a00e6]██[/#8a00e6][cyan]║[/cyan]      [#8a00e6]██████[/#8a00e6][cyan]╔╝[/cyan]   [#8a00e6]██[/#8a00e6][cyan]║[/cyan]        [dim]•[/dim] [white]dev-env[/white]        [dim]•[/dim] [white]monitoring[/white]                      [blue]║[/blue]
[blue]║[/blue]  [cyan]╚═╝[/cyan]      [cyan]╚═════╝[/cyan]    [cyan]╚═╝[/cyan]                                                           [blue]║[/blue]
[blue]║[/blue]                                                                                    [blue]║[/blue]
[blue]║[/blue]        [bold bright_blue]FIXBOT TERMINAL[/bold bright_blue]        [dim]>[/dim] [italic white]awaiting intelligent command...[/italic white]                    [blue]║[/blue]
[blue]║[/blue]                                                                                    [blue]║[/blue]
[blue]║[/blue][cyan]                   ✦                               ★                                [/cyan][blue]║[/blue]
[blue]║[/blue][cyan]                                                                                    [/cyan][blue]║[/blue]
[blue]║[/blue][cyan]          ★                                             ☽                           [/cyan][blue]║[/blue]
[blue]║[/blue][cyan]                      ·                     ✦                                       [/cyan][blue]║[/blue]
[blue]╚════════════════════════════════════════════════════════════════════════════════════╝[/blue]"""

THEME_CYAN = """[cyan]╔════════════════════════════════════════════════════════════════════════════════════╗[/cyan]
[cyan]║[/cyan][blue]  ★        ☽        ★                                                               [/blue][cyan]║[/cyan]
[cyan]║[/cyan][blue]          ·                                         ·                               [/blue][cyan]║[/cyan]
[cyan]║[/cyan][blue]                  ✦                      ★                                          [/blue][cyan]║[/cyan]
[cyan]║[/cyan]                                                                                    [cyan]║[/cyan]
[cyan]║[/cyan]  [#00ffff]███████[/#00ffff][blue]╗[/blue] [#00ffff]██████[/#00ffff][blue]╗[/blue] [#00ffff]████████[/#00ffff][blue]╗[/blue]     [yellow]★[/yellow]  [bold white]AI SYSTEM SUPPORT[/bold white]  [yellow]☽[/yellow]                            [cyan]║[/cyan]
[cyan]║[/cyan]  [#00e6e6]██[/#00e6e6][blue]╔════╝[/blue] [#00e6e6]██[/#00e6e6][blue]╔══[/blue][#00e6e6]██[/#00e6e6][blue]╗╚══[/blue][#00e6e6]██[/#00e6e6][blue]╔══╝[/blue]                                                        [cyan]║[/cyan]
[cyan]║[/cyan]  [#00cccc]█████[/#00cccc][blue]╗[/blue]   [#00cccc]██████[/#00cccc][blue]╔╝[/blue]   [#00cccc]██[/#00cccc][blue]║[/blue]        [dim]•[/dim] [white]network[/white]        [dim]•[/dim] [white]diagnostics[/white]                     [cyan]║[/cyan]
[cyan]║[/cyan]  [#00b3b3]██[/#00b3b3][blue]╔══╝[/blue]   [#00b3b3]██[/#00b3b3][blue]╔══[/blue][#00b3b3]██[/#00b3b3][blue]╗[/blue]   [#00b3b3]██[/#00b3b3][blue]║[/blue]        [dim]•[/dim] [white]installer[/white]      [dim]•[/dim] [white]storage[/white]                         [cyan]║[/cyan]
[cyan]║[/cyan]  [#009999]██[/#009999][blue]║[/blue]      [#009999]██████[/#009999][blue]╔╝[/blue]   [#009999]██[/#009999][blue]║[/blue]        [dim]•[/dim] [white]dev-env[/white]        [dim]•[/dim] [white]monitoring[/white]                      [cyan]║[/cyan]
[cyan]║[/cyan]  [blue]╚═╝[/blue]      [blue]╚═════╝[/blue]    [blue]╚═╝[/blue]                                                           [cyan]║[/cyan]
[cyan]║[/cyan]                                                                                    [cyan]║[/cyan]
[cyan]║[/cyan]        [bold bright_cyan]FIXBOT TERMINAL[/bold bright_cyan]        [dim]>[/dim] [italic white]awaiting intelligent command...[/italic white]                    [cyan]║[/cyan]
[cyan]║[/cyan]                                                                                    [cyan]║[/cyan]
[cyan]║[/cyan][blue]                   ✦                               ★                                [/blue][cyan]║[/cyan]
[cyan]║[/cyan][blue]                                                                                    [/blue][cyan]║[/cyan]
[cyan]║[/cyan][blue]          ★                                             ☽                           [/blue][cyan]║[/cyan]
[cyan]║[/cyan][blue]                      ·                     ✦                                       [/blue][cyan]║[/cyan]
[cyan]╚════════════════════════════════════════════════════════════════════════════════════╝[/cyan]"""

THEMES = {
    "1": ("Yellow Theme (Golden)", THEME_YELLOW),
    "2": ("Purple Theme (ASCII MOTION)", THEME_PURPLE),
    "3": ("Cyan Theme (Cyberpunk)", THEME_CYAN),
}

CURRENT_THEME = "1"


from rich.align import Align

def print_banner() -> None:
    console.print()
    banner_text = THEMES[CURRENT_THEME][1]
    console.print(Align.center(banner_text))
    console.print(Align.center(
        "\n  Type your problem in plain English.  "
        "[bold white]help[/bold white]"
        " [dim].[/dim] [bold white]scan[/bold white]"
        " [dim].[/dim] [bold white]tickets[/bold white]"
        " [dim].[/dim] [bold white]exit[/bold white]\n"
    ))

def ask_theme() -> None:
    global CURRENT_THEME
    time.sleep(1.5)
    console.print("\n  [bold white]Theme Selection[/bold white]")
    console.print("  [dim]───────────────[/dim]")
    for k, v in THEMES.items():
        console.print(f"  [bold cyan][{k}][/bold cyan] {v[0]}")
    
    console.print()
    choice = Prompt.ask("  [bold cyan]❯[/bold cyan] Select theme", choices=list(THEMES.keys()), default=CURRENT_THEME)
    
    sys.stdout.write("\033[1A\r\033[2K")
    sys.stdout.flush()

    if choice in THEMES:
        CURRENT_THEME = choice
        console.print(f"  [bold green]✓[/bold green] [dim]Applied: {THEMES[choice][0]}[/dim]")

def get_theme_color() -> str:
    if CURRENT_THEME == "1": return "yellow"
    if CURRENT_THEME == "2": return "magenta"
    if CURRENT_THEME == "3": return "cyan"
    return "cyan"

def get_theme_hex() -> str:
    if CURRENT_THEME == "1": return "#ffff55"
    if CURRENT_THEME == "2": return "#d484ff"
    if CURRENT_THEME == "3": return "#00ffff"
    return "#00ffff"

def print_welcome_panel() -> None:
    from rich.panel import Panel
    from rich.box import Box
    LEFT_LINE = Box(
        "    \n"
        "│   \n"
        "│   \n"
        "│   \n"
        "│   \n"
        "│   \n"
        "│   \n"
        "    \n"
    )
    theme_col = get_theme_color()
    text = f"""[bold black on {theme_col}] Fixbot v4.0 [/bold black on {theme_col}] [{theme_col}] Autonomous Support Engineer [/{theme_col}]

[white]Hello! I'm Fixbot - your AI-powered system support engineer. I can diagnose and fix real issues on your machine.[/white]

[dim white]I use Gemini 1.5 Flash to reason about live OS data - not pre-written FAQ answers. Every response is based on your actual system state.[/dim white]

[dim white]Tell me what's wrong and I'll analyse your system, find the root cause, and walk you through the fix - or do it automatically with your permission.[/dim white]

[dim]Modules active: [{theme_col}]network[/{theme_col}] · [{theme_col}]storage[/{theme_col}] · [{theme_col}]dev-env[/{theme_col}] · [{theme_col}]system-health[/{theme_col}] · [{theme_col}]dependency[/{theme_col}][/dim]"""

    console.print(Panel(text, box=LEFT_LINE, border_style=theme_col))
    console.print()

def print_help() -> None:
    table = Table(show_edge=False, box=None, padding=(0, 2))
    table.add_column("Command", style="bold cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_row("scan",              "Full system report across all modules")
    table.add_row("processes / ps",   "List running processes sorted by CPU%")
    table.add_row("tabs / live tabs", "List browser tabs/windows (remote debugging if available)")
    table.add_row("kill <pid>",       "Terminate a process by PID, name, or index")
    table.add_row("install <app>",    "Look up and run the install command for any app or package")
    table.add_row("tickets",          "List saved support tickets")
    table.add_row("ticket <id>",      "View a specific ticket in detail")
    table.add_row("report / reports", "List recent diagnostic reports")
    table.add_row("clear",            "Clear the screen")
    table.add_row("exit / quit",      "Exit fixbot")
    console.print()
    console.print(table)
    console.print()
