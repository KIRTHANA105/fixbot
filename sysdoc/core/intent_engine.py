from typing import Dict, List


class IntentEngine:
    def __init__(self) -> None:
        self.intent_map: Dict[str, List[str]] = {
            "GREETING": [
                "hi", "hello", "hey", "greetings",
                "good morning", "good afternoon", "good evening", "how are you",
            ],
            "NETWORK": [
                "slow internet", "wifi", "wi-fi", "no internet", "dns", "ping",
                "isp", "connection", "speed", "packet loss", "outage", "latency",
                "router", "still slow", "retest", "network", "speedtest",
                "signal", "bandwidth",
            ],
            "STORAGE": [
                "c drive", "disk full", "no space", "storage", "full", "duplicate",
                "partition", "d drive", "temp files", "recycle bin", "large files",
                "disk usage", "junk", "clean disk", "low storage", "e drive",
                "shrink", "extend",
            ],
            "DEV_ENV": [
                "pip", "pip install", "python", "module not found", "import error",
                "venv", "virtualenv", "node", "npm", "vs code", "path",
                "dependency", "conflict", "requirements", "build fail", "corrupted",
                "broken install", "dev environment", "python error", "pypi",
            ],
            "SYSTEM": [
                "crash", "restart", "bsod", "blue screen", "freeze", "heat",
                "cpu", "ram", "overheating", "slow pc", "lagging", "memory",
                "fan", "temperature", "hang", "startup slow", "memory leak",
                "process", "task manager", "tabs", "live tabs", "open tabs",
                "browser tabs",
            ],
            "SCAN": [
                "scan", "full scan", "check all", "diagnose", "everything",
                "health check", "system check", "full report", "all modules",
            ],
            "TICKET": [
                "ticket", "escalate", "technician", "report", "help desk",
                "create ticket", "open ticket", "support",
            ],
            "INSTALL": [
                "install", "download", "how to install", "how do i install",
                "i want to install", "i need to install", "can you install",
                "get me", "setup", "grab",
            ],
        }

    def detect_intent(self, user_input: str) -> str:
        lowered = user_input.lower()
        # Fix #21 — weight multi-word keywords higher so "how to install" (3 words)
        # beats a single "install" match in another category.
        scores: Dict[str, float] = {cat: 0.0 for cat in self.intent_map}

        for category, keywords in self.intent_map.items():
            for keyword in keywords:
                if keyword in lowered:
                    scores[category] += len(keyword.split())

        best_category = "GENERAL"
        best_score = 0.0
        tie = False

        for category, score in scores.items():
            if score > best_score:
                best_score = score
                best_category = category
                tie = False
            elif score == best_score and score > 0:
                tie = True

        if best_score == 0 or tie:
            return "GENERAL"

        return best_category
