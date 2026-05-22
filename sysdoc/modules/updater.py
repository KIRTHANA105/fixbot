import json
import shutil
import subprocess
from typing import Optional


class UpdateScanner:
    """Scans winget, pip, and npm for available package updates."""

    # ── public ────────────────────────────────────────────────────────────

    def scan_all(self) -> list[dict]:
        results: list[dict] = []
        results.extend(self.scan_winget())
        results.extend(self.scan_pip())
        results.extend(self.scan_npm())
        return results

    def scan_winget(self) -> list[dict]:
        if not shutil.which("winget"):
            return []
        try:
            proc = subprocess.run(
                ["winget", "upgrade", "--accept-source-agreements"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=40,
            )
            return self._parse_winget(proc.stdout)
        except Exception:
            return []

    def scan_pip(self) -> list[dict]:
        if not shutil.which("pip"):
            return []
        try:
            proc = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=20,
            )
            packages = json.loads(proc.stdout or "[]")
            return [
                {
                    "name":    p["name"],
                    "id":      p["name"],
                    "from":    p["version"],
                    "to":      p["latest_version"],
                    "source":  "pip",
                    "manager": "pip",
                }
                for p in packages
            ]
        except Exception:
            return []

    def scan_npm(self) -> list[dict]:
        if not shutil.which("npm"):
            return []
        try:
            proc = subprocess.run(
                ["npm", "outdated", "-g", "--json"],
                capture_output=True,
                text=True,
                timeout=20,
            )
            data = json.loads(proc.stdout or "{}")
            return [
                {
                    "name":    name,
                    "id":      name,
                    "from":    info.get("current", "?"),
                    "to":      info.get("latest", "?"),
                    "source":  "npm",
                    "manager": "npm",
                }
                for name, info in data.items()
            ]
        except Exception:
            return []

    def get_update_cmd(self, item: dict) -> list[str]:
        mgr = item["manager"]
        if mgr == "winget":
            return [
                "winget", "upgrade",
                "--id", item["id"],
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        if mgr == "pip":
            return ["pip", "install", "--upgrade", item["name"]]
        if mgr == "npm":
            return ["npm", "update", "-g", item["name"]]
        return []

    # ── winget table parser ────────────────────────────────────────────────

    def _parse_winget(self, output: str) -> list[dict]:
        lines = output.splitlines()

        # Find the header row (contains all four column labels)
        header_idx: Optional[int] = None
        for i, line in enumerate(lines):
            if ("Name" in line and "Id" in line
                    and "Version" in line and "Available" in line):
                header_idx = i
                break
        if header_idx is None:
            return []

        header = lines[header_idx]
        # Derive column positions from where each header word starts.
        # winget uses a single solid separator line (no gaps), so we cannot
        # use the separator to detect columns — we must use the header itself.
        col_starts = self._col_starts_from_header(header)
        if len(col_starts) < 4:
            return []

        results: list[dict] = []
        for line in lines[header_idx + 2:]:   # skip header + separator
            stripped = line.strip()
            if not stripped:
                continue
            # "30 upgrades available." — stop
            if stripped[0].isdigit() and "upgrade" in stripped.lower():
                break
            # Pure separator lines
            if all(c in ("-", "─", " ") for c in line):
                continue

            fields = []
            for k, start in enumerate(col_starts):
                end   = col_starts[k + 1] if k + 1 < len(col_starts) else len(line)
                value = line[start:end].strip() if start < len(line) else ""
                fields.append(value)

            if len(fields) < 4 or not fields[0] or not fields[1]:
                continue

            results.append({
                "name":    fields[0],
                "id":      fields[1],
                "from":    fields[2],
                "to":      fields[3],
                "source":  fields[4] if len(fields) > 4 else "winget",
                "manager": "winget",
            })

        return results

    @staticmethod
    def _col_starts_from_header(header: str) -> list[int]:
        """Return sorted column start positions found in the winget header row."""
        positions: list[int] = []
        for word in ("Name", "Id", "Version", "Available", "Source"):
            idx = header.find(word)
            if idx != -1:
                positions.append(idx)
        return sorted(positions)
