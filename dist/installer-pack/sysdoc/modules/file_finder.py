import os
import re
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import psutil

MAX_RESULTS = 20
_MAX_READ_BYTES = 100 * 1024  # 100 KB

_SKIP_DIRS = frozenset({
    # Windows system noise
    "$Recycle.Bin", "System Volume Information", "WinSxS", "winsxs",
    "MpEngine", "SoftwareDistribution", "CbsTemp", "Panther",
    "assembly", "GAC_MSIL", "GAC_64", "GAC_32", "NativeImages",
    # App caches and temp — these produce irrelevant duplicate results
    "Cache", "cache", "CacheStorage", "Code Cache",
    "GPUCache", "ShaderCache", "DawnCache",
    "Temp", "temp",
    "Recent",           # Windows Recent shortcuts (.lnk files)
    "Crash Reports", "CrashReports",
    # Known noisy app dirs
    "claude-cli-nodejs", "node_modules", ".git",
})

# File extensions that are never the real target — skip silently
_SKIP_EXTENSIONS = frozenset({
    ".lnk",   # Windows shortcuts (in Recent, Desktop shortcuts to other places)
    ".tmp",
    ".log",
    ".db",
    ".db-shm",
    ".db-wal",
})

# Directories to search FIRST — order matters, most relevant at the top
def _build_priority_dirs() -> List[str]:
    home = os.path.expanduser("~")
    onedrive = os.path.join(home, "OneDrive")
    candidates = [
        # Desktop (regular + OneDrive-synced)
        os.path.join(home, "Desktop"),
        os.path.join(onedrive, "Desktop"),
        # Common user folders
        os.path.join(home, "Documents"),
        os.path.join(onedrive, "Documents"),
        os.path.join(home, "Downloads"),
        os.path.join(onedrive, "Downloads"),
        # OneDrive root (synced files)
        onedrive,
        # Home dir itself
        home,
        # Installed apps
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        # Other users (last before full scan)
        "C:\\Users",
    ]
    # Deduplicate while preserving order
    seen: set = set()
    result = []
    for d in candidates:
        d_norm = os.path.normcase(d)
        if d_norm not in seen and os.path.isdir(d):
            seen.add(d_norm)
            result.append(d)
    return result


def _get_drives() -> List[str]:
    drives = []
    try:
        for part in psutil.disk_partitions(all=False):
            if part.fstype and "cdrom" not in part.opts:
                drives.append(part.mountpoint)
    except Exception:
        pass
    return drives or ["C:\\"]


def _safe_size(path: str) -> Optional[int]:
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def _build_variants(query_lower: str) -> List[str]:
    """Build search variants for a query so 'any desk' also matches 'anydesk'."""
    variants = [query_lower]
    if " " in query_lower:
        variants.append(query_lower.replace(" ", ""))       # "any desk" → "anydesk"
        variants.append(query_lower.replace(" ", "-"))      # "any desk" → "any-desk"
        variants.append(query_lower.replace(" ", "_"))      # "any desk" → "any_desk"
    return variants


def _matches(name_lower: str, variants: List[str]) -> bool:
    return any(v in name_lower for v in variants)


def _walk_for_query(
    root: str, query_lower: str, results: List[Dict], seen: set
) -> bool:
    """Walk root searching for query. Returns True when MAX_RESULTS reached."""
    variants = _build_variants(query_lower)
    try:
        for dirpath, dirs, files in os.walk(root, topdown=True):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]

            for d in dirs:
                if _matches(d.lower(), variants):
                    full = os.path.join(dirpath, d)
                    if full not in seen:
                        seen.add(full)
                        results.append({"type": "folder", "name": d, "path": full, "size": None})
                        if len(results) >= MAX_RESULTS:
                            return True

            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in _SKIP_EXTENSIONS:
                    continue
                if _matches(f.lower(), variants):
                    full = os.path.join(dirpath, f)
                    if full not in seen:
                        seen.add(full)
                        results.append({
                            "type": "file",
                            "name": f,
                            "path": full,
                            "size": _safe_size(full),
                        })
                        if len(results) >= MAX_RESULTS:
                            return True
    except (PermissionError, OSError):
        pass
    return False


def _search_in_path_env(query_lower: str) -> List[Dict]:
    """Use 'where' to find executables registered in PATH."""
    results = []
    # Try all variants (e.g. "any desk" → also try "anydesk")
    candidates = list(dict.fromkeys(_build_variants(query_lower)))
    for term in candidates:
        try:
            proc = subprocess.run(
                ["where", term],
                capture_output=True, text=True, timeout=4,
            )
            for line in proc.stdout.strip().splitlines():
                line = line.strip()
                if line and os.path.isfile(line):
                    path_lower = line.lower()
                    if not any(r["path"].lower() == path_lower for r in results):
                        results.append({
                            "type": "app",
                            "name": os.path.basename(line),
                            "path": line,
                            "size": _safe_size(line),
                        })
        except Exception:
            pass
    return results


def search_system(query: str) -> List[Dict]:
    """Search all drives for files/folders/apps whose name contains query."""
    query_lower = query.lower().strip()
    results: List[Dict] = []
    seen: set = set()

    # Phase 0: executables in PATH (fast)
    for r in _search_in_path_env(query_lower):
        if r["path"] not in seen:
            seen.add(r["path"])
            results.append(r)
    if len(results) >= MAX_RESULTS:
        return results

    # Phase 1: high-value directories (fast)
    for d in _build_priority_dirs():
        if _walk_for_query(d, query_lower, results, seen):
            return results

    # Phase 2: full drive scan
    for drive in _get_drives():
        if _walk_for_query(drive, query_lower, results, seen):
            return results

    return results


def _force_remove_readonly(func, path, exc_info):
    """Clear read-only flag and retry — required for .git folders on Windows."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def delete_path(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"Path not found: {path}"
        if p.is_dir():
            shutil.rmtree(path, onerror=_force_remove_readonly)
            return f"Deleted folder: {path}"
        try:
            p.unlink()
        except PermissionError:
            os.chmod(path, stat.S_IWRITE)
            p.unlink()
        return f"Deleted file: {path}"
    except Exception as e:
        return f"Delete failed: {e}"


def rename_path(path: str, new_name: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"Path not found: {path}"
        new_path = p.parent / new_name
        if new_path.exists():
            return f"Already exists: {new_path}"
        p.rename(new_path)
        return f"Renamed to: {new_path}"
    except Exception as e:
        return f"Rename failed: {e}"


def copy_to_clipboard(path: str) -> str:
    try:
        subprocess.run(["clip"], input=path.encode("utf-8"), capture_output=True)
        return f"Path copied to clipboard: {path}"
    except Exception as e:
        return f"Clipboard copy failed: {e}"


def read_file_safe(path: str) -> Optional[str]:
    """Read a text file up to 100 KB. Returns None if binary or unreadable."""
    try:
        size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="strict") as f:
            content = f.read(_MAX_READ_BYTES)
        if size > _MAX_READ_BYTES:
            content += f"\n\n[...truncated — file is {format_size(size)}, showing first 100 KB]"
        return content
    except UnicodeDecodeError:
        return None  # binary file
    except Exception:
        return None


def format_size(n: Optional[int]) -> str:
    if n is None:
        return "—"
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}" if value != int(value) else f"{int(value)} {unit}"
        value /= 1024
    return f"{value:.1f} PB"
