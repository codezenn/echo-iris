"""
Echo IRIS - Chat Memory
Sliding window conversation history with JSON persistence.
Stores the last MAX_HISTORY messages (user + assistant pairs).
Atomic write pattern to prevent corruption on power loss.

Usage:
    from chat_memory import ChatMemory
    mem = ChatMemory()
    mem.add("user", "What is your name?")
    mem.add("assistant", "I am IRIS.")
    messages = mem.get_messages()       # list of {"role": ..., "content": ...}
    mem.clear()                         # clear history (e.g. on personality switch)
"""

import json
import os

MEMORY_PATH = os.path.expanduser("~/echo-iris/software/chat_memory.json")
MAX_HISTORY = 16  # 16 messages ~ 2880 tokens, fits in 4096 num_ctx with system prompt


class ChatMemory:
    def __init__(self, path=MEMORY_PATH, max_history=MAX_HISTORY):
        self.path = path
        self.max_history = max_history
        self.history = self._load()

    def _load(self):
        """Load history from disk, or return empty list."""
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data[-self.max_history:]
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def _save(self):
        """Atomic write: .tmp, fsync, os.replace."""
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(self.history, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.path)

    def add(self, role, content):
        """Add a message and trim to MAX_HISTORY. Saves immediately."""
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        self._save()

    def get_messages(self):
        """Return the current history as a list of message dicts.
        Ready to insert into the Ollama messages array.
        """
        return list(self.history)

    def clear(self):
        """Clear all history and save. Call on personality switch."""
        self.history = []
        self._save()

    def count(self):
        """Return number of messages in history."""
        return len(self.history)
