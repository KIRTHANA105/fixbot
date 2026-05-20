import hashlib
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import psutil

from sysdoc.config import THRESHOLDS


class StorageModule:
    def collect(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "drives": [],
            "critical_drives": [],
            "temp_folder_path": os.environ.get("TEMP", "/tmp"),
            "temp_folder_gb": 0.0,
            "recycle_bin_gb": 0.0,
            "top_large_files": [],
            # Fix #8 — duplicate scan removed from collect(); it is on-demand only
            # (called by executor._fix_storage_duplicates or explicit user request)
            "duplicates_note": "run 'fix duplicates' to scan",
        }

        try:
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                except Exception:
                    continue
                drive_info = {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "free_gb": round(usage.free / (1024 ** 3), 2),
                    "used_pct": round(usage.percent, 1),
                }
                result["drives"].append(drive_info)
                if drive_info["used_pct"] > THRESHOLDS["disk_critical"]:
                    result["critical_drives"].append(drive_info["device"])
        except Exception as error:
            result["error"] = f"drive enumeration failed: {error}"

        try:
            temp_path = Path(result["temp_folder_path"])
            result["temp_folder_gb"] = round(self._directory_size(temp_path) / (1024 ** 3), 2)
        except Exception as error:
            result["error"] = result.get("error", "") + f" temp scan failed: {error}"

        try:
            result["recycle_bin_gb"] = round(self._recycle_bin_size() / (1024 ** 3), 2)
        except Exception as error:
            result["error"] = result.get("error", "") + f" recycle bin scan failed: {error}"

        try:
            result["top_large_files"] = self._find_top_large_files()
        except Exception as error:
            result["error"] = result.get("error", "") + f" large file scan failed: {error}"

        if "error" in result and not result["error"]:
            result.pop("error", None)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _directory_size(self, path: Path) -> int:
        total = 0
        if not path.exists():
            return 0
        for root, _, files in os.walk(path):
            for name in files:
                try:
                    fp = Path(root) / name
                    if fp.is_file():
                        total += fp.stat().st_size
                except Exception:
                    continue
        return total

    def _recycle_bin_size(self) -> int:
        if platform.system().lower() != "windows":
            return 0
        try:
            import winshell
            total = 0
            for item in winshell.recycle_bin():
                try:
                    total += item.size
                except Exception:
                    continue
            return total
        except Exception:
            recycle_path = Path(os.environ.get("SystemDrive", "C:") + "\\$Recycle.Bin")
            return self._directory_size(recycle_path)

    def _candidate_dirs(self) -> List[Path]:
        home = Path.home()
        candidates = [home / "Downloads", home / "Documents"]
        return [p for p in candidates if p.exists()]

    def _find_top_large_files(self) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        for directory in self._candidate_dirs():
            for root, _, names in os.walk(directory):
                for name in names:
                    try:
                        fp = Path(root) / name
                        if not fp.is_file():
                            continue
                        files.append({
                            "name": name,
                            "path": str(fp),
                            "size_mb": round(fp.stat().st_size / (1024 ** 2), 2),
                        })
                    except Exception:
                        continue
        files.sort(key=lambda item: item["size_mb"], reverse=True)
        return files[:10]

    def _duplicate_waste_size(self, paths: List[str]) -> int:
        if len(paths) < 2:
            return 0
        try:
            sizes = [Path(p).stat().st_size for p in paths if Path(p).is_file()]
            return sum(sizes[1:])
        except Exception:
            return 0

    def find_duplicates(self, scan_dirs: List[str]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for scan_dir in scan_dirs:
            root_path = Path(scan_dir)
            if not root_path.exists():
                continue
            for root, _, names in os.walk(root_path):
                for name in names:
                    fp = Path(root) / name
                    try:
                        if not fp.is_file():
                            continue
                        size = fp.stat().st_size
                        if size > 500 * 1024 * 1024:
                            continue
                        file_hash = self._md5(fp)
                        if not file_hash:
                            continue
                        groups.setdefault(file_hash, []).append(str(fp))
                    except Exception:
                        continue
        return {h: paths for h, paths in groups.items() if len(paths) > 1}

    def _md5(self, file_path: Path) -> str:
        digest = hashlib.md5()
        try:
            with file_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(8192), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Fix actions
    # ------------------------------------------------------------------

    def fix_temp(self) -> str:
        temp_path = Path(os.environ.get("TEMP", "/tmp"))
        freed_bytes = 0
        skipped = 0
        if not temp_path.exists():
            return "Temp folder not found"
        for root, _, names in os.walk(temp_path):
            for name in names:
                fp = Path(root) / name
                try:
                    if fp.is_file():
                        freed_bytes += fp.stat().st_size
                        fp.unlink()
                except Exception:
                    skipped += 1
        return f"Freed {freed_bytes / (1024 ** 3):.2f} GB ({skipped} files skipped)"

    def fix_recycle_bin(self) -> str:
        if platform.system().lower() != "windows":
            return "Recycle bin fix not supported on this platform"
        try:
            import winshell
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
            return "Recycle Bin emptied"
        except Exception:
            try:
                recycle_path = Path(os.environ.get("SystemDrive", "C:") + "\\$Recycle.Bin")
                # Fix #18 — remove shell=True with a list; use shell=False
                subprocess.run(
                    ["rd", "/s", "/q", str(recycle_path)],
                    check=False,
                    shell=False,
                )
                return "Recycle Bin emptied"
            except Exception as error:
                return f"Recycle Bin cleanup failed: {error}"

    def fix_delete_duplicates(self, duplicates_dict: Dict[str, List[str]]) -> str:
        # Fix #24 — move to Recycle Bin instead of permanent delete
        try:
            import send2trash
            _trash = send2trash.send2trash
        except ImportError:
            try:
                import winshell as _ws
                def _trash(path: str) -> None:
                    _ws.delete_file(path, no_confirm=True, allow_undo=True)
            except ImportError:
                _trash = None

        deleted = 0
        groups = 0
        for paths in duplicates_dict.values():
            if len(paths) < 2:
                continue
            groups += 1
            for duplicate_path in sorted(paths)[1:]:
                try:
                    if _trash is not None:
                        _trash(duplicate_path)
                    else:
                        Path(duplicate_path).unlink()
                    deleted += 1
                except Exception:
                    continue

        action = "Moved to Recycle Bin" if _trash is not None else "Deleted"
        return f"{action}: {deleted} duplicate files across {groups} groups"

    def partition_wizard(self, os_data: Dict[str, Any]) -> str:
        if platform.system().lower() != "windows":
            return "Partition wizard only supported on Windows"

        # Fix #16 — use Rich + prompt_toolkit instead of raw print/input
        from prompt_toolkit import prompt as tk_prompt
        from prompt_toolkit.styles import Style
        from rich.console import Console
        from rich.table import Table

        console = Console()
        style = Style.from_dict({"prompt": "#00c6ff"})

        drives = [
            d for d in psutil.disk_partitions(all=False)
            if not d.device.upper().startswith("C:")
        ]
        if not drives:
            return "No non-C drives available for partition wizard"

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Drive")
        table.add_column("Free GB")
        table.add_column("Total GB")
        for d in drives:
            try:
                usage = psutil.disk_usage(d.mountpoint)
                table.add_row(
                    d.device,
                    f"{usage.free / (1024**3):.2f}",
                    f"{usage.total / (1024**3):.2f}",
                )
            except Exception:
                continue
        console.print(table)

        try:
            source_drive = tk_prompt(
                "  Enter source drive letter to shrink (e.g. D:): ", style=style
            ).strip().upper()
        except (KeyboardInterrupt, EOFError):
            return "Partition wizard cancelled"

        matching = [d for d in drives if d.device.upper().startswith(source_drive)]
        if not matching:
            return "Invalid source drive selected"

        try:
            usage = psutil.disk_usage(matching[0].mountpoint)
        except Exception as error:
            return f"Unable to read drive usage: {error}"

        free_gb = usage.free / (1024 ** 3)
        max_take = free_gb * 0.7
        try:
            raw = tk_prompt(
                f"  Enter GB to take (min 5, max {max_take:.1f}): ", style=style
            )
            amount_gb = float(raw.strip())
        except (KeyboardInterrupt, EOFError):
            return "Partition wizard cancelled"
        except ValueError:
            return "Invalid number entered"

        if amount_gb < 5 or amount_gb > max_take:
            return "Requested size not within allowed range"

        volume_number = self._get_volume_number(source_drive)
        if volume_number is None:
            return "Unable to determine diskpart volume number"

        script_path = Path(tempfile.gettempdir()) / "sysdoc_partition.txt"
        shrink_size = int(amount_gb * 1024)
        script_content = f"select volume {volume_number}\nshrink desired={shrink_size}\n"
        script_path.write_text(script_content, encoding="utf-8")

        console.print(f"\n  [dim]Script to run:[/dim]\n  [yellow]{script_content.strip()}[/yellow]\n")

        try:
            confirm = tk_prompt("  Apply? [y/n]: ", style=style).strip().lower()
        except (KeyboardInterrupt, EOFError):
            return "Partition wizard cancelled"

        if confirm != "y":
            return "Partition wizard cancelled"

        try:
            result = subprocess.run(
                ["diskpart", "/s", str(script_path)],
                capture_output=True,
                text=True,
                shell=False,
            )
            output = result.stdout + result.stderr
            if "successfully" in output.lower():
                new_data = self.collect()
                return f"Partition shrink applied.\n{new_data['drives']}"
            return f"DiskPart failed:\n{output.strip()}"
        except Exception as error:
            return f"DiskPart execution failed: {error}"

    def _get_volume_number(self, drive_letter: str) -> Any:
        script_path = Path(tempfile.gettempdir()) / "sysdoc_volume_lookup.txt"
        script_path.write_text("list volume\n", encoding="utf-8")
        result = subprocess.run(
            ["diskpart", "/s", str(script_path)],
            capture_output=True,
            text=True,
            shell=False,
        )
        output = result.stdout + result.stderr
        for line in output.splitlines():
            if drive_letter in line and "Volume" in line:
                for part in line.split():
                    if part.isdigit():
                        return int(part)
        return None
