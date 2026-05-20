from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from display.banner import get_theme_color

console = Console()

def print_user(text: str) -> None:
    console.print()
    console.print(f"  [bold blue]YOU[/bold blue] [dim]>[/dim] {text}")

def print_bot_start() -> None:
    theme_col = get_theme_color()
    console.print()
    console.print(f"  [bold {theme_col}]FIXBOT[/bold {theme_col}] [dim]>[/dim] ", end="")

def print_ok(text: str) -> None:
    console.print(f"  [bold green]✓[/bold green] [dim]{text}[/dim]")

def print_warn(text: str) -> None:
    console.print(f"  [bold yellow]⚠[/bold yellow] [dim]{text}[/dim]")

def print_err(text: str) -> None:
    console.print(f"  [bold red]✗[/bold red] [red]{text}[/red]")

def print_info(text: str) -> None:
    console.print(f"  [bold blue]ℹ[/bold blue] [dim]{text}[/dim]")

def print_data(key: str, value: str) -> None:
    theme_col = get_theme_color()
    console.print(f"    [{theme_col}]✦[/{theme_col}] [dim]{key}:[/dim] [white]{value}[/white]")

def print_collecting(module: str) -> None:
    theme_col = get_theme_color()
    console.print(f"  [bold {theme_col}]◉[/bold {theme_col}] [dim]Analyzing {module} subsystem...[/dim]")

def print_section(title: str) -> None:
    theme_col = get_theme_color()
    console.print()
    console.print(f"  [bold {theme_col}]╭─ {title.upper()} ───────────────────────[/bold {theme_col}]")


def print_ticket(ticket: dict) -> None:
    priority = str(ticket.get("priority", "LOW")).upper()
    badge_color = "green"
    if priority == "HIGH":
        badge_color = "red"
    elif priority == "MEDIUM":
        badge_color = "yellow"

    status = ticket.get("status", "OPEN")
    title = f"Ticket [{ticket.get('id', 'unknown')}]"
    body = Text()
    body.append(f"Status: ", style="dim")
    body.append(f"{status}\n", style="bold white")
    body.append(f"Priority: ", style="dim")
    body.append(f"{priority}\n", style=badge_color)
    body.append(f"Problem: ", style="dim")
    body.append(f"{ticket.get('problem', 'n/a')}\n", style="white")
    body.append(f"Created: ", style="dim")
    body.append(f"{ticket.get('created', 'n/a')}", style="white")

    theme_col = get_theme_color()
    console.print(Panel(body, title=f"[bold {theme_col}]{title}[/]", subtitle=f"[dim]Module: {ticket.get('module', 'unknown')}[/dim]", subtitle_align="right", box=box.ROUNDED, border_style=theme_col))


def print_system_scan(all_data: dict) -> None:
    theme_col = get_theme_color()
    table = Table(show_header=True, header_style=f"bold {theme_col}", box=box.ROUNDED, border_style=theme_col)
    table.add_column("Subsystem", style=f"bold {theme_col}")
    table.add_column("Diagnostic Summary", style="white")

    for module, data in all_data.items():
        summary = _summarize_value(data)
        table.add_row(module.upper(), summary)

    console.print()
    console.print(table)


def _summarize_value(value: object) -> str:
    if isinstance(value, dict):
        items = []
        for key, item in value.items():
            if len(items) >= 6:
                items.append("...")
                break
            items.append(f"{key}={_summarize_value(item)}")
        return ", ".join(items)
    if isinstance(value, list):
        if not value:
            return "[]"
        if isinstance(value[0], dict):
            return ", ".join(str(v.get("name", str(v))) for v in value[:3]) + ("..." if len(value) > 3 else "")
        return ", ".join(str(item) for item in value[:6]) + ("..." if len(value) > 6 else "")
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def print_process_table(procs: list) -> None:
    theme_col = get_theme_color()
    table = Table(show_header=True, header_style=f"bold {theme_col}", box=box.ROUNDED, border_style="dim", padding=(0, 2))
    table.add_column("IDX",       style="dim",     width=4,  no_wrap=True)
    table.add_column("PID",     style="yellow",  width=7,  no_wrap=True)
    table.add_column("Process Name",    style="white",   width=36, no_wrap=True)
    table.add_column("CPU %",    style="green",   width=6,  no_wrap=True)
    table.add_column("RAM %",    style="magenta", width=6,  no_wrap=True)
    table.add_column("Files",   style="cyan",    width=6,  no_wrap=True)
    table.add_column("Status",  style="dim",     width=10, no_wrap=True)

    for idx, proc in enumerate(procs, start=1):
        cpu = proc.get("cpu_pct", 0.0)
        cpu_style = "bold red" if cpu > 50 else ("yellow" if cpu > 20 else "green")
        open_files = proc.get("open_files", -1)
        files_str = str(open_files) if open_files >= 0 else "n/a"
        table.add_row(
            str(idx),
            str(proc.get("pid", "?")),
            proc.get("name", "unknown"),
            f"[{cpu_style}]{cpu}[/{cpu_style}]",
            str(proc.get("ram_pct", 0.0)),
            files_str,
            proc.get("status", "?"),
        )

    console.print()
    console.print(f"  [bold {theme_col}]ACTIVE PROCESSES[/bold {theme_col}] [dim]— Ranked by CPU Utilization[/dim]")
    console.print(table)
    console.print(f"  [{theme_col}]❯[/] [dim]kill <pid_or_name>  —  terminate a process by PID or name[/dim]")
    console.print()


def print_browser_tab_table(tabs: list) -> None:
    theme_col = get_theme_color()
    if not tabs:
        console.print(f"\n  [bold yellow]⚠[/bold yellow] [dim]No active browser instances detected.[/dim]\n")
        return

    table = Table(show_header=True, header_style=f"bold {theme_col}", box=box.ROUNDED, border_style="dim", padding=(0, 2))
    table.add_column("IDX",        style="dim",     width=4,  no_wrap=True)
    table.add_column("Browser",  style="green",   width=9,  no_wrap=True)
    table.add_column("PID",      style="yellow",  width=7,  no_wrap=True)
    table.add_column("CPU %",     style="magenta", width=6,  no_wrap=True)
    table.add_column("RAM %",     style="cyan",    width=6,  no_wrap=True)
    table.add_column("Page Title",    style="white",   no_wrap=True)

    remote_tabs = any(tab.get("source") == "remote_tab" for tab in tabs)

    for idx, tab in enumerate(tabs, start=1):
        cpu = tab.get("cpu_pct", 0.0)
        cpu_style = "bold red" if cpu > 30 else ("yellow" if cpu > 10 else "magenta")
        table.add_row(
            str(idx),
            tab.get("browser", "?"),
            str(tab.get("pid", "?")),
            f"[{cpu_style}]{cpu}[/{cpu_style}]",
            str(tab.get("ram_pct", 0.0)),
            tab.get("title", ""),
        )

    console.print()
    console.print(f"  [bold {theme_col}]LIVE BROWSER TABS[/bold {theme_col}] [dim]— {len(tabs)} instances found[/dim]")
    console.print(table)
    if remote_tabs:
        console.print(f"  [bold blue]ℹ[/bold blue] [dim]Individual Chrome tabs discovered via remote debugging.[/dim]")
    else:
        console.print(f"  [bold yellow]⚠[/bold yellow] [dim]No remote-debug tabs discovered. Start Chrome with --remote-debugging-port=9222 to isolate tabs.[/dim]")
    console.print(f"  [{theme_col}]❯[/] [dim]kill <pid_or_name_or_index>  —  close a browser tab/window by PID, name, or # index[/dim]")
    console.print()
