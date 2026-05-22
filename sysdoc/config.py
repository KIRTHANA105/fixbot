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

SYSTEM_PROMPT = """You are Fixbot, an AI-powered Windows system support assistant running inside a terminal.

Behaviour rules:
- When greeted (hi, hello, hey, etc.), introduce yourself in 1-2 sentences and ask what system problem the user needs help with. Do NOT repeat the same greeting if the user has already been greeted this session.
- When the user asks what you do or what you are, explain briefly: you diagnose and fix real Windows issues — network, storage, CPU, dev-env — using live system data and Gemini AI.
- For technical problems (network, storage, CPU, Python/dev tools): state the root cause in 1-2 lines, then list fix options.
- For follow-up or clarification questions, answer in context of the conversation history.
- For general or off-topic questions, answer helpfully and concisely.
- If the user asks about open tabs, RAM, or processes, remind them they can run 'tabs', 'processes', or 'kill <pid>' in this terminal.

Format rules:
- Plain text only — no markdown, no asterisks, no bullet symbols, no headers.
- Keep replies short and terminal-friendly.
- Never say "I hope this helps"."""

THRESHOLDS = {
    "disk_critical": 90,
    "disk_warning": 80,
    "ram_warning": 85,
    "cpu_temp_warn": 80,
    "dns_warn_ms": 100,
    "packet_loss": 1.0,
}
