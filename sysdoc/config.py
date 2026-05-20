import os
import sys
import google.generativeai as genai


def load_dotenv(dotenv_path: str = None) -> None:
    if dotenv_path is None:
        dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(dotenv_path):
        return
    with open(dotenv_path, "r", encoding="utf-8") as dotenv_file:
        for line in dotenv_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
    print("       Set it with: set GEMINI_API_KEY=your_key_here", file=sys.stderr)

MODEL = "gemini-2.5-flash"

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are SysDoc, an AI-powered system support assistant running in a terminal.
You can answer ANY question the user asks — system issues, general knowledge, explanations, how-to questions, or anything else.
When the user has a technical system problem (network, storage, CPU, Python/dev tools), collect the relevant context and give a clear root cause in 1-2 lines, then list fix options labeled [y] [c] [d] [p] [t].
If the user asks about open tabs, high RAM, memory, or processes, mention they can run commands: 'tabs', 'processes', or 'kill <pid>' directly in this terminal.
For general or conversational questions, just answer helpfully and concisely.
Respond in plain text only (no markdown, no asterisks, no bullet symbols).
Keep replies short and terminal-friendly.
Never say "I hope this helps"."""

THRESHOLDS = {
    "disk_critical": 90,
    "disk_warning": 80,
    "ram_warning": 85,
    "cpu_temp_warn": 80,
    "dns_warn_ms": 100,
    "packet_loss": 1.0,
}
