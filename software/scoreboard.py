"""
Echo IRIS - Demo Scoreboard
Tracks total conversations and per-date counts.
Uses atomic write (write to .tmp, fsync, os.replace) to prevent corruption.

Usage:
    from scoreboard import Scoreboard
    sb = Scoreboard()
    sb.increment()                    # after each completed exchange
    print(sb.get_summary())           # "12 total conversations today, 47 all time."
    print(sb.check_trigger(text))     # returns summary string if triggered, else None
"""

import json
import os
import time
from datetime import date

STATS_PATH = os.path.expanduser("~/echo-iris/software/conversation_stats.json")


class Scoreboard:
    def __init__(self, path=STATS_PATH):
        self.path = path
        self.stats = self._load()

    def _load(self):
        """Load stats from disk, or create default if missing."""
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"total": 0, "by_date": {}}

    def _save(self):
        """Atomic write: write to .tmp, fsync, os.replace."""
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(self.stats, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.path)

    def increment(self):
        """Increment total and today's count. Call after each completed exchange."""
        today = date.today().isoformat()
        self.stats["total"] += 1
        self.stats["by_date"][today] = self.stats["by_date"].get(today, 0) + 1
        self._save()

    def get_total(self):
        return self.stats["total"]

    def get_today(self):
        today = date.today().isoformat()
        return self.stats["by_date"].get(today, 0)

    def get_summary(self):
        """Return a speakable summary string."""
        today_count = self.get_today()
        total = self.get_total()
        if total == 0:
            return "I haven't had any conversations yet. You are my first."
        if today_count == 0:
            return f"I have had {total} conversations in total, but none yet today."
        return f"{today_count} conversations today, {total} in total."

    def check_trigger(self, text):
        """Check if recognized text asks about conversation count.
        Returns speakable summary string if triggered, None otherwise.
        """
        text_lower = text.lower()
        triggers = [
            "how many conversations",
            "how many times have we talked",
            "how many chats",
            "conversation count",
            "scoreboard",
            "how popular",
        ]
        for trigger in triggers:
            if trigger in text_lower:
                return self.get_summary()
        return None
