import inspect
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, Optional, Tuple

from rich.console import Console

from .gemini_client import GeminiClient
from .intent_engine import IntentEngine
from .prompt_builder import PromptBuilder
from .verifier import Verifier, VerificationResult
from sysdoc.modules.dev_env import DevEnvironmentModule
from sysdoc.modules.network import NetworkModule
from sysdoc.modules.storage import StorageModule
from sysdoc.modules.system_health import SystemHealthModule
from sysdoc.tickets.ticket_manager import TicketManager

_DANGEROUS_PATTERNS = [
    "format", "wipe", "factory reset", "delete all", "rm -rf",
    "drop table", "truncate", "destroy",
]

FIX_TIMEOUT_SECONDS = 60


class SysDocExecutor:
    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.intent_engine = IntentEngine()
        self.gemini = GeminiClient()
        self.console = Console()

        # Fix #1 — single instances shared with PromptBuilder (no duplicates)
        self.network = NetworkModule()
        self.storage = StorageModule()
        self.system_health = SystemHealthModule()
        self.dev_env = DevEnvironmentModule()

        self.prompt_builder = PromptBuilder(
            network=self.network,
            storage=self.storage,
            dev_env=self.dev_env,
            system_health=self.system_health,
        )

        self.ticket_manager = TicketManager()
        self.verifier = Verifier()

        # Fix #15 — persistent thread pool instead of one-per-fix
        self._fix_pool = ThreadPoolExecutor(max_workers=1)

        self.last_verification: Optional[VerificationResult] = None

        self.FIX_MAP = {
            ("NETWORK", "f"): (self.network.fix_dns,                  "Flushing DNS + switching to 8.8.4.4"),
            ("NETWORK", "r"): (self.network.fix_reset_adapter,        "Resetting Wi-Fi adapter"),
            ("STORAGE", "c"): (self._fix_storage_cleanup,             "Cleaning temp and Recycle Bin"),
            ("STORAGE", "d"): (self._fix_storage_duplicates,          "Removing duplicate files"),
            ("STORAGE", "p"): (self.storage.partition_wizard,         "Launching partition wizard"),
            ("DEV_ENV", "y"): (self.dev_env.fix_path,                 "Fixing Python PATH"),
            ("DEV_ENV", "c"): (self.dev_env.fix_pip,                  "Repairing pip"),
            ("DEV_ENV", "v"): (self.dev_env.fix_rebuild_venv,         "Rebuilding virtual environment"),
            ("SYSTEM",  "k"): (self.system_health.fix_kill_processes, "Killing high-RAM processes"),
            ("SYSTEM",  "p"): (self.system_health.fix_power_balanced, "Setting power plan to Balanced"),
        }

    def __del__(self) -> None:
        try:
            self._fix_pool.shutdown(wait=False)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------------

    def _is_safe(self, description: str) -> bool:
        desc_lower = description.lower()
        return not any(pattern in desc_lower for pattern in _DANGEROUS_PATTERNS)

    # ------------------------------------------------------------------
    # Fix execution
    # ------------------------------------------------------------------

    def _call_fix_with_timeout(self, fix_function: Any, os_data: Dict[str, Any]) -> Any:
        future = self._fix_pool.submit(self._call_fix_function, fix_function, os_data)
        try:
            return future.result(timeout=FIX_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            raise TimeoutError(f"Fix timed out after {FIX_TIMEOUT_SECONDS}s")

    def run(
        self, intent: str, action: str, os_data: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        intent_key = (intent or "").upper()
        action_key = (action or "").lower()

        if action_key == "t":
            return self._run_ticket_action(intent_key, os_data)

        mapping_key = (intent_key, action_key)
        if mapping_key not in self.FIX_MAP:
            self.console.print(f"No fix mapped for {intent_key} / {action_key}", style="yellow")
            return ("unsupported", os_data)

        fix_function, description = self.FIX_MAP[mapping_key]

        if not self._is_safe(description):
            self.console.print(f"  [red][BLOCKED][/red] Unsafe operation refused: {description}")
            return ("blocked", os_data)

        if self.dry_run:
            self.console.print(f"  [yellow][DRY RUN][/yellow] Would execute: {description}")
            return (f"[dry-run] {description}", os_data)

        self.console.print(f"  running: {description}...", style="dim")

        before_snapshot = self.verifier.snapshot(intent_key)

        try:
            result = self._call_fix_with_timeout(fix_function, os_data)
        except TimeoutError as error:
            self.console.print(f"[!] {error}", style="bold red")
            return ("timeout", os_data)
        except Exception as error:
            self.console.print(f"[!] Fix failed: {error}", style="bold red")
            return ("failed", os_data)

        response = str(result or "")
        for line in response.splitlines():
            self.console.print(line)

        after_snapshot = self.verifier.snapshot(intent_key)
        verification = self.verifier.verify(intent_key, before_snapshot, after_snapshot)
        self.verifier.display(verification)
        self.last_verification = verification

        new_os_data = self.prompt_builder.build_context("", intent_key)
        self._report_changes(os_data, new_os_data)
        return (response, new_os_data)

    def _call_fix_function(self, function: Any, os_data: Dict[str, Any]) -> Any:
        signature = inspect.signature(function)
        if len(signature.parameters) > 0:
            return function(os_data)
        return function()

    def _fix_storage_cleanup(self, os_data: Dict[str, Any]) -> str:
        temp_result = self.storage.fix_temp()
        recycle_result = self.storage.fix_recycle_bin()
        return f"{temp_result}\n{recycle_result}"

    def _fix_storage_duplicates(self) -> str:
        candidate_dirs = [str(p) for p in self.storage._candidate_dirs()]
        duplicates = self.storage.find_duplicates(candidate_dirs)
        return self.storage.fix_delete_duplicates(duplicates)

    def _run_ticket_action(
        self, intent_key: str, os_data: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        self.console.print("  running: creating ticket...", style="dim")
        try:
            result = self.ticket_manager.create_ticket(
                problem="auto-created by executor",
                os_data=os_data,
                gemini_reply="",
                module=intent_key,
            )
        except Exception as error:
            self.console.print(f"[!] Ticket creation failed: {error}", style="bold red")
            return ("failed", os_data)

        new_os_data = self.prompt_builder.build_context("", intent_key)
        self._report_changes(os_data, new_os_data)
        return (str(result), new_os_data)

    def _report_changes(
        self, old_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> None:
        for key in sorted(set(old_data).intersection(new_data)):
            if old_data.get(key) != new_data.get(key):
                self.console.print(f"[OK] {key}: {old_data[key]} → {new_data[key]}")
