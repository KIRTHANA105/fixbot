import platform
import re
import socket
import subprocess
import time
from typing import Dict, Any, List, Union

import psutil

from sysdoc.config import THRESHOLDS


class NetworkModule:
    def collect(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "wifi_ssid": "unknown",
            "active_adapters": [],
            "gateway_ip": "unknown",
            "gateway_ping_ms": "unreachable",
            "dns_primary_ms": "unreachable",
            "dns_secondary_ms": "unreachable",
            "dns_status": "SLOW",
            "internet": "UNREACHABLE",
            "packet_loss_pct": 100.0,
            "outage_prediction": "none detected",
            "wifi_signal_dbm": "unavailable",
        }

        try:
            stats = psutil.net_if_stats()
            data["active_adapters"] = [name for name, iface in stats.items() if iface.isup]
        except Exception as error:
            data["error"] = f"adapter scan failed: {error}"

        try:
            data["gateway_ip"] = self._get_gateway_ip()
        except Exception as error:
            data["error"] = data.get("error", "") + f" gateway parse failed: {error}"

        try:
            gateway = data["gateway_ip"]
            if gateway and gateway != "unknown":
                data["gateway_ping_ms"] = self._ping(gateway)
        except Exception as error:
            data["error"] = data.get("error", "") + f" gateway ping failed: {error}"

        try:
            data["dns_primary_ms"] = self._ping("8.8.8.8")
            data["dns_secondary_ms"] = self._ping("8.8.4.4")
        except Exception as error:
            data["error"] = data.get("error", "") + f" dns ping failed: {error}"

        try:
            if isinstance(data["dns_primary_ms"], int) and data["dns_primary_ms"] > THRESHOLDS["dns_warn_ms"]:
                data["dns_status"] = "SLOW"
            else:
                data["dns_status"] = "OK"
        except Exception:
            data["dns_status"] = "SLOW"

        try:
            data["internet"] = self._check_internet()
        except Exception as error:
            data["error"] = data.get("error", "") + f" internet check failed: {error}"

        try:
            data["packet_loss_pct"] = self._measure_packet_loss("8.8.8.8", count=5)
        except Exception as error:
            data["error"] = data.get("error", "") + f" packet loss check failed: {error}"

        try:
            if isinstance(data["packet_loss_pct"], float) and data["packet_loss_pct"] > 1.0 and data["dns_status"] == "SLOW":
                data["outage_prediction"] = "LIKELY — ISP-side degradation"
            else:
                data["outage_prediction"] = "none detected"
        except Exception:
            data["outage_prediction"] = "none detected"

        try:
            data["wifi_signal_dbm"] = self._get_wifi_signal_dbm()
        except Exception as error:
            data["error"] = data.get("error", "") + f" wifi signal parse failed: {error}"

        try:
            data["wifi_ssid"] = self._get_wifi_ssid()
        except Exception as error:
            data["error"] = data.get("error", "") + f" wifi ssid parse failed: {error}"

        if "error" in data and not data["error"]:
            data.pop("error", None)

        return data

    def _get_gateway_ip(self) -> str:
        current_platform = platform.system().lower()
        if current_platform == "windows":
            # Primary: route print gives reliable gateway for all adapter types
            # including mobile hotspots where ipconfig may show nothing
            try:
                output = self._run_command(["route", "print", "0.0.0.0"])
                gateway = self._parse_gateway_from_route_print(output)
                if gateway and gateway != "unknown":
                    return gateway
            except Exception:
                pass
            # Fallback: ipconfig
            output = self._run_command(["ipconfig"])
            return self._parse_gateway_from_ipconfig(output)
        output = self._run_command(["ip", "route"]) if current_platform == "linux" else ""
        return self._parse_gateway_from_ip_route(output)

    def _parse_gateway_from_route_print(self, output: str) -> str:
        # Output has lines like:  0.0.0.0   0.0.0.0   192.168.43.1   192.168.43.x  25
        # We want the 3rd column (gateway) on the default route line
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("0.0.0.0"):
                parts = stripped.split()
                if len(parts) >= 3:
                    candidate = parts[2]
                    # Validate it looks like an IP and isn't a catch-all
                    if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", candidate) and not candidate.startswith("0."):
                        return candidate
        return "unknown"

    def _run_command(self, command: List[str]) -> str:
        result = subprocess.run(command, capture_output=True, text=True, shell=False)
        return result.stdout or result.stderr or ""

    def _parse_gateway_from_ipconfig(self, output: str) -> str:
        matches = re.findall(r"Default Gateway[\s\.]*:[\s]*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", output, re.IGNORECASE)
        for ip in matches:
            if ip and not ip.startswith("0."):
                return ip
        return "unknown"

    def _parse_gateway_from_ip_route(self, output: str) -> str:
        match = re.search(r"default via ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", output)
        return match.group(1) if match else "unknown"

    def _ping(self, host: str) -> Union[int, str]:
        current_platform = platform.system().lower()
        command = []
        if current_platform == "windows":
            command = ["ping", "-n", "1", "-w", "1000", host]
        else:
            command = ["ping", "-c", "1", "-W", "1", host]

        output = self._run_command(command)
        return self._parse_ping_time(output)

    def _parse_ping_time(self, output: str) -> Union[int, str]:
        match = re.search(r"time[=<]\s*([0-9]+(?:\.[0-9]+)?)\s*ms", output, re.IGNORECASE)
        if not match:
            return "unreachable"
        return int(float(match.group(1)))

    def _measure_packet_loss(self, host: str, count: int = 5) -> float:
        current_platform = platform.system().lower()
        if current_platform == "windows":
            command = ["ping", "-n", str(count), host]
        else:
            command = ["ping", "-c", str(count), host]

        output = self._run_command(command)
        return self._parse_packet_loss(output)

    def _parse_packet_loss(self, output: str) -> float:
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)%.*loss", output, re.IGNORECASE)
        if match:
            return float(match.group(1))
        match = re.search(r"Lost = [0-9]+ \(([0-9]+)% loss\)", output, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 100.0

    def _check_internet(self) -> str:
        try:
            socket.gethostbyname("google.com")
            return "reachable"
        except Exception:
            return "UNREACHABLE"

    def _get_wifi_signal_dbm(self) -> Union[int, str]:
        current_platform = platform.system().lower()
        if current_platform == "windows":
            output = self._run_command(["netsh", "wlan", "show", "interfaces"])
            return self._parse_windows_wifi_signal(output)
        output = self._run_command(["iwconfig"]) if current_platform == "linux" else ""
        return self._parse_linux_wifi_signal(output)

    def _get_wifi_ssid(self) -> str:
        current_platform = platform.system().lower()
        if current_platform == "windows":
            output = self._run_command(["netsh", "wlan", "show", "interfaces"])
            match = re.search(r"^\s*SSID\s*:\s*(.+)$", output, re.IGNORECASE | re.MULTILINE)
            return match.group(1).strip() if match else "not connected"
        if current_platform == "linux":
            output = self._run_command(["iwgetid", "-r"])
            return output.strip() or "not connected"
        return "unavailable"

    def _parse_windows_wifi_signal(self, output: str) -> Union[int, str]:
        match = re.search(r"Signal\s*:\s*([0-9]+)%", output, re.IGNORECASE)
        if not match:
            return "unavailable"
        percent = int(match.group(1))
        return self._signal_percent_to_dbm(percent)

    def _parse_linux_wifi_signal(self, output: str) -> Union[int, str]:
        match = re.search(r"Signal level[=:]\s*(-?[0-9]+)\s*dBm", output)
        if not match:
            return "unavailable"
        return int(match.group(1))

    def _signal_percent_to_dbm(self, percent: int) -> int:
        return max(-100, min(-30, int(percent * 0.7) - 100))

    def fix_dns(self) -> str:
        try:
            if platform.system().lower() != "windows":
                return "DNS fix not supported on this platform"
            subprocess.run(["ipconfig", "/flushdns"], check=False, capture_output=True, text=True)
            result = subprocess.run(
                ["netsh", "interface", "ip", "set", "dns", "Wi-Fi", "static", "8.8.4.4"],
                check=False,
                capture_output=True,
                text=True,
                shell=False,
            )
            return result.stdout.strip() or result.stderr.strip() or "dns fix executed"
        except Exception as error:
            return f"dns fix failed: {error}"

    def fix_reset_adapter(self) -> str:
        try:
            if platform.system().lower() != "windows":
                return "adapter reset not supported on this platform"
            subprocess.run(
                ["netsh", "interface", "set", "interface", "Wi-Fi", "disable"],
                check=False,
                capture_output=True,
                text=True,
                shell=False,
            )
            time.sleep(2)
            result = subprocess.run(
                ["netsh", "interface", "set", "interface", "Wi-Fi", "enable"],
                check=False,
                capture_output=True,
                text=True,
                shell=False,
            )
            return result.stdout.strip() or result.stderr.strip() or "adapter reset executed"
        except Exception as error:
            return f"adapter reset failed: {error}"

    def generate_isp_report(self, os_data: Dict[str, Any]) -> str:
        lines: List[str] = ["ISP report summary:"]
        for key in [
            "wifi_ssid",
            "active_adapters",
            "gateway_ip",
            "gateway_ping_ms",
            "dns_primary_ms",
            "dns_secondary_ms",
            "dns_status",
            "internet",
            "packet_loss_pct",
            "outage_prediction",
            "wifi_signal_dbm",
        ]:
            value = os_data.get(key, "unknown")
            lines.append(f"{key}: {value}")
        if "error" in os_data:
            lines.append(f"error: {os_data['error']}")
        return "\n".join(lines)
