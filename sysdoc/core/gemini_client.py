from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import google.generativeai as genai
from google.api_core import exceptions

from sysdoc.config import MODEL, SYSTEM_PROMPT


@dataclass
class GeminiChunk:
    text: str


class GeminiClient:
    def __init__(self) -> None:
        self.model_name = MODEL
        self.system_prompt = SYSTEM_PROMPT
        # Fix #9 — cache the model instance instead of creating one per call
        self._model = genai.GenerativeModel(MODEL, system_instruction=SYSTEM_PROMPT)

    def format_os_data(self, os_data: Dict[str, object]) -> str:
        return "\n".join(f"  {k}: {v}" for k, v in os_data.items())

    def _format_history(self, history: List[Dict[str, List[str]]]) -> str:
        lines: List[str] = []
        for entry in history[-12:]:
            role = entry.get("role", "unknown")
            for part in entry.get("parts", []):
                lines.append(f"{role}: {part}")
        return "\n".join(lines)

    def _build_prompt(
        self,
        user_input: str,
        os_data: Dict[str, object],
        history: List[Dict[str, List[str]]],
    ) -> str:
        # Fix #4 — system_prompt is passed as system_instruction to the model;
        # do NOT prepend it here again or it is sent twice.
        formatted_data = self.format_os_data(os_data)
        history_text = self._format_history(history)
        message = (
            f"User problem: {user_input}\n\n"
            f"Collected system data:\n{formatted_data}\n\n"
            "Give root cause and fix options."
        )
        parts: List[str] = []
        if history_text:
            parts += ["Previous exchange:", history_text, ""]
        parts.append(message)
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Offline fallback
    # ------------------------------------------------------------------

    def _mock_response(self, user_input: str, os_data: Dict[str, object]) -> str:
        parts = [
            "\n  [bold red]OFFLINE FALLBACK[/bold red] [dim]— Gemini AI is currently unreachable[/dim]",
            "  [dim]Analyzing local system telemetry metrics for anomalies...[/dim]",
            ""
        ]

        anomalies = 0

        cpu = os_data.get("cpu_percent", 0)
        if isinstance(cpu, (int, float)) and cpu > 80:
            parts.append(f"  [bold yellow]⚠[/bold yellow] [bold white]CPU Load High[/bold white] [dim]({cpu}%)[/dim]\n    [dim]↳ Close background tasks or check runaway processes.[/dim]")
            anomalies += 1
        else:
            parts.append(f"  [bold green]✓[/bold green] [dim]CPU utilization stable ({cpu}%)[/dim]")

        ram = os_data.get("ram_used_pct", 0)
        if isinstance(ram, (int, float)) and ram > 80:
            parts.append(f"  [bold yellow]⚠[/bold yellow] [bold white]RAM Exhaustion[/bold white] [dim]({ram}%)[/dim]\n    [dim]↳ Terminate memory-hungry programs.[/dim]")
            anomalies += 1
        else:
            parts.append(f"  [bold green]✓[/bold green] [dim]RAM utilization stable ({ram}%)[/dim]")

        drives = os_data.get("drives", [])
        disk_warning = False
        if isinstance(drives, list):
            for drive in drives:
                free = drive.get("free_gb", 999) if isinstance(drive, dict) else 999
                if isinstance(free, (int, float)) and free < 5:
                    device = drive.get("device", "Drive") if isinstance(drive, dict) else "Drive"
                    parts.append(
                        f"  [bold red]✗[/bold red] [bold white]Low Disk Space on {device}[/bold white] [dim]({free} GB free)[/dim]\n    [dim]↳ Execute storage cleanup protocol [c].[/dim]"
                    )
                    disk_warning = True
                    anomalies += 1
                    break
        if not disk_warning:
            parts.append("  [bold green]✓[/bold green] [dim]Storage levels secure.[/dim]")

        internet = os_data.get("internet")
        if internet is False or (isinstance(internet, str) and "unreachable" in internet.lower()):
            parts.append("  [bold red]✗[/bold red] [bold white]Internet Disconnected[/bold white]\n    [dim]↳ Try DNS flush [f] or adapter reset [r].[/dim]")
            anomalies += 1
        else:
            parts.append("  [bold green]✓[/bold green] [dim]Network connection established.[/dim]")

        dns = os_data.get("dns_status")
        if isinstance(dns, str) and "fail" in dns.lower():
            parts.append("  [bold red]✗[/bold red] [bold white]DNS Resolution Fail[/bold white]\n    [dim]↳ Flush local DNS resolver cache [f].[/dim]")
            anomalies += 1

        parts.append("")
        if anomalies == 0:
            parts.append("  [dim]System metrics look normal. Reconnect network to recover AI features.[/dim]")
        else:
            parts.append(f"  [dim]{anomalies} anomalies flagged in offline mode. Resolve issues to continue.[/dim]")
        
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Blocking call (installer / scan)
    # ------------------------------------------------------------------

    def ask_gemini(
        self,
        user_input: str,
        os_data: Dict[str, object],
        history: List[Dict[str, List[str]]],
    ) -> str:
        prompt = self._build_prompt(user_input, os_data, history)
        try:
            response = self._model.generate_content(prompt)

            if isinstance(response, str):
                return response.strip() or "Gemini returned an empty response."
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "text") and candidate.text:
                    return candidate.text.strip()
                if isinstance(candidate, str) and candidate:
                    return candidate.strip()
            return "Gemini returned an empty response."
        except (exceptions.GoogleAPICallError, Exception):
            return self._mock_response(user_input, os_data)

    def generate(self, prompt: str) -> str:
        """Blocking, no-history call used by the installer and scan."""
        try:
            response = self._model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return "Gemini unavailable — working offline"

    # ------------------------------------------------------------------
    # Fix #5 — real streaming using Gemini's stream=True
    # ------------------------------------------------------------------

    def ask_gemini_stream(
        self,
        user_input: str,
        os_data: Dict[str, object],
        history: List[Dict[str, List[str]]],
    ) -> Iterable[GeminiChunk]:
        prompt = self._build_prompt(user_input, os_data, history)
        try:
            response = self._model.generate_content(prompt, stream=True)
            has_content = False
            for chunk in response:
                text = getattr(chunk, "text", None)
                if text:
                    has_content = True
                    yield GeminiChunk(text=text)
            if not has_content:
                yield GeminiChunk(text="Gemini returned an empty response.")
        except (exceptions.GoogleAPICallError, Exception):
            yield GeminiChunk(text=self._mock_response(user_input, os_data))
