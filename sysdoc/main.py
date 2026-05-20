import os
import sys

from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
from rich.console import Console

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.conversation_memory import ConversationMemory
from core.executor import SysDocExecutor
from core.permission_gate import PermissionGate
from core.report_generator import ReportGenerator
from modules.installer import InstallerModule, extract_app_name
from display.banner import print_banner, print_help, ask_theme, get_theme_color, get_theme_hex, print_welcome_panel
from display.formatter import (
    print_bot_start,
    print_collecting,
    print_data,
    print_err,
    print_info,
    print_ok,
    print_process_table,
    print_browser_tab_table,
    print_section,
    print_ticket,
    print_user,
    print_system_scan,
    print_warn,
)
from tickets.ticket_manager import TicketManager

console = Console()

_DRY_RUN = "--dry-run" in sys.argv
_MEMORY_PATH = os.path.join(ROOT_DIR, "memory", "conversation.json")
_REPORTS_DIR = os.path.join(ROOT_DIR, "reports")

COMMANDS = {
    "exit": "exit",
    "quit": "exit",
    "clear": "clear",
    "help": "help",
    "scan": "scan",
    "tickets": "tickets",
    "processes": "processes",
    "ps": "processes",
    "tabs": "tabs",
    "live tabs": "tabs",
    "report": "report",
    "reports": "report",
}

def format_ticket_detail(ticket: dict) -> str:
    lines = []
    for key, value in ticket.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


_INTENT_PRIORITY_KEYS = {
    "NETWORK":  ["wifi_ssid", "internet", "download_mbps", "upload_mbps", "dns_status", "ping_ms", "packet_loss_pct", "gateway_ip", "outage_prediction"],
    "STORAGE":  ["drives", "critical_drives", "temp_folder_gb", "recycle_bin_gb", "top_large_files"],
    "DEV_ENV":  ["active_python", "pip_status", "dependency_conflicts", "node_version", "venv_found"],
    "SYSTEM":   ["cpu_percent", "ram_used_pct", "cpu_temp_c", "recent_crashes", "fan_speed_rpm"],
}

_DEFAULT_PRIORITY_KEYS = [
    "wifi_ssid", "cpu_percent", "ram_used_pct", "cpu_temp_c",
    "dns_status", "internet", "outage_prediction", "gateway_ip",
    "packet_loss_pct", "temp_folder_gb", "recycle_bin_gb",
]


def _top_os_data_keys(os_data: dict, intent: str = "") -> list:
    priority_keys = _INTENT_PRIORITY_KEYS.get(intent, _DEFAULT_PRIORITY_KEYS)
    keys = [key for key in priority_keys if key in os_data]
    keys.extend(k for k in os_data.keys() if k not in keys)
    return keys[:5]


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        console.print(
            "\n  [bold red]GEMINI_API_KEY is not set.[/bold red]"
            "\n  Add it to your environment or create a .env file with:"
            "\n  [dim]GEMINI_API_KEY=your_api_key_here[/dim]\n"
        )
        return

    if not PermissionGate.has_admin():
        console.print(
            "\n  [bold red]fixbot requires administrator privileges.[/bold red]"
            "\n  Right-click your terminal and choose 'Run as administrator', then try again.\n"
        )
        return

    executor = SysDocExecutor(dry_run=_DRY_RUN)
    prompt_builder = executor.prompt_builder
    ticket_manager = TicketManager()
    memory = ConversationMemory(path=_MEMORY_PATH)
    report_gen = ReportGenerator(reports_dir=_REPORTS_DIR)
    installer = InstallerModule(executor.gemini)

    print_banner()
    ask_theme()
    PermissionGate.ask_initial_permissions()
    print_welcome_panel()



    if _DRY_RUN:
        print_warn("DRY RUN mode — fixes will be previewed but not executed.")

    while True:
        try:
            hex_col = get_theme_hex()
            user_input = prompt(
                "\n  ❯ ",
                style=Style.from_dict({"prompt": f"{hex_col} bold"}),
            ).strip()

        except (KeyboardInterrupt, EOFError):
            console.print("\n  Goodbye.\n")
            break

        if not user_input:
            continue

        user_input_lower = user_input.lower().strip()
        action = None
        filter_arg = ""

        if user_input_lower in COMMANDS:
            action = COMMANDS[user_input_lower]
        elif user_input_lower.startswith("live tabs"):
            action = "tabs"
            filter_arg = user_input[9:].strip()
        else:
            parts = user_input.split(maxsplit=1)
            if parts:
                first_word = parts[0].lower()
                if first_word in COMMANDS:
                    action = COMMANDS[first_word]
                    if len(parts) == 2:
                        filter_arg = parts[1].strip()

        if action is not None:
            if action == "exit":
                console.print("  Shutting down.\n")
                break
            if action == "clear":
                console.clear()
                print_banner()
                continue
            if action == "help":
                print_help()
                continue
            if action == "scan":
                all_data = {
                    "network": executor.network.collect(),
                    "storage": executor.storage.collect(),
                    "dev_env": executor.dev_env.collect(),
                    "system": executor.system_health.collect(),
                }
                print_system_scan(all_data)
                continue
            if action == "report":
                recent = report_gen.list_recent()
                if not recent:
                    print_info("No reports yet. Reports are saved automatically after each fix.")
                else:
                    print_info(f"Last {len(recent)} reports:")
                    for path in recent:
                        console.print(f"  [dim]{path}[/dim]")
                continue
            if action == "tickets":
                summaries = ticket_manager.list_tickets()
                if not summaries:
                    print_info("No tickets found.")
                    continue
                for summary in summaries:
                    print_ticket(summary)
                continue
            if action == "processes":
                procs = executor.system_health.list_processes(top=20, filter_name=filter_arg)
                print_process_table(procs)
                continue
            if action == "tabs":
                tabs = executor.system_health.list_browser_tabs(filter_name=filter_arg)
                print_browser_tab_table(tabs)
                continue

        if user_input.lower().startswith("ticket "):
            ticket_id = user_input.split(maxsplit=1)[1].strip()
            ticket = ticket_manager.get_ticket(ticket_id)
            if not ticket:
                print_warn(f"Ticket {ticket_id} not found.")
                continue
            print_ticket(ticket)
            console.print(format_ticket_detail(ticket))
            continue

        if user_input.lower().startswith("kill "):
            parts = user_input.split(maxsplit=1)
            if len(parts) == 2:
                target = parts[1].strip()
                result = executor.system_health.kill_by_index_or_pid(target)
                if "Killed" in result or "Closed" in result:
                    print_ok(result)
                else:
                    print_warn(result)
            else:
                print_warn("Usage: kill <pid_or_name_or_index>   example: kill 1 or kill 1234 or kill whatsapp")
            continue

        print_user(user_input)

        app_name = extract_app_name(user_input)
        if app_name:
            installer.handle(app_name)
            memory.add("user", user_input)
            memory.add("model", f"Handled install request for: {app_name}")
            console.print()
            continue

        intent = executor.intent_engine.detect_intent(user_input)

        if memory.is_followup(user_input) and intent == "GENERAL":
            recent = memory.get_history(6)
            if recent:
                for entry in reversed(recent):
                    if entry["role"] == "user":
                        prev_intent = executor.intent_engine.detect_intent(entry["parts"][0])
                        if prev_intent != "GENERAL":
                            intent = prev_intent
                            break

        if intent == "GREETING":
            greeting = "Hello! I am Fixbot, your AI-powered system support assistant. How can I help you today?"
            print_bot_start()
            console.print(greeting)
            memory.add("user", user_input)
            memory.add("model", greeting)
            console.print()
            continue

        if intent == "GENERAL":
            # Send general/unknown questions directly to Gemini — no clarification menu
            pass

        diagnostic_intents = {"NETWORK", "STORAGE", "DEV_ENV", "SYSTEM"}
        if intent in diagnostic_intents:
            print_collecting(intent.lower())
            os_data = prompt_builder.build_context(user_input, intent)
            for key in _top_os_data_keys(os_data, intent):
                print_data(key, str(os_data.get(key, "n/a")))
        else:
            os_data = {}

        console.print()
        print_bot_start()
        full_reply = ""
        theme_col = get_theme_color()
        for chunk in executor.gemini.ask_gemini_stream(user_input, os_data, memory.get_history()):
            text = getattr(chunk, "text", str(chunk))
            console.print(text, style=theme_col, end="", highlight=False)
            full_reply += text
        console.print()

        memory.add("user", user_input)
        memory.add("model", full_reply)

        # Only offer fix actions for intents that have mapped fixes
        actionable_intents = {"NETWORK", "STORAGE", "DEV_ENV", "SYSTEM"}
        if intent in actionable_intents:
            action = PermissionGate.ask_permission(intent)
            if action == "t":
                ticket = ticket_manager.create_ticket(
                    problem=user_input,
                    os_data=os_data,
                    gemini_reply=full_reply,
                    module=intent,
                )
                print_ticket(ticket)
            elif action == "n":
                print_info("Skipped.")
            elif action == "d":
                console.print(full_reply)
            else:
                result, new_data = executor.run(intent, action, os_data)
                os_data = new_data

                verification = executor.last_verification
                report = report_gen.generate(
                    intent=intent,
                    problem=user_input,
                    os_data=os_data,
                    ai_reply=full_reply,
                    fix_applied=result,
                    verification_passed=verification.passed if verification else None,
                    changes=verification.changes if verification else {},
                )
                saved = report_gen.save(report)
                report_gen.display_summary(report, saved_path=saved)

        console.print()


if __name__ == "__main__":
    main()
