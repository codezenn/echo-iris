"""
Echo IRIS - Personality Manager
Handles personality mode switching via voice commands.

Usage:
    from personality_manager import PersonalityManager
    pm = PersonalityManager()
    pm.current_name()                    # "Professional"
    pm.get_system_prompt()               # current system prompt string
    pm.get_temperature()                 # current temperature float
    result = pm.check_switch(text)       # returns announce string if switched, else None
"""

import json
import os
import re

PERSONALITIES_PATH = os.path.expanduser("~/echo-iris/software/personalities.json")

# Voice command patterns: "switch to pirate", "pirate mode", "professional mode", etc.
SWITCH_PATTERNS = [
    re.compile(r"switch\s+to\s+(professional|playful|pirate|parrot)", re.IGNORECASE),
    re.compile(r"(professional|playful|pirate|parrot)\s+mode", re.IGNORECASE),
    re.compile(r"be\s+(professional|playful|pirate|parrot)", re.IGNORECASE),
    re.compile(r"go\s+(professional|playful|pirate|parrot)", re.IGNORECASE),
]


class PersonalityManager:
    def __init__(self, path=PERSONALITIES_PATH, default="professional"):
        with open(path, "r") as f:
            self.personalities = json.load(f)
        self.current = default

    def current_name(self):
        return self.personalities[self.current]["name"]

    def get_system_prompt(self):
        return self.personalities[self.current]["system_prompt"]

    def get_temperature(self):
        return self.personalities[self.current]["temperature"]

    def check_switch(self, text):
        """Check if text contains a personality switch command.
        Returns the announce string if switched, None otherwise.
        The caller should clear conversation history after a switch.
        """
        for pattern in SWITCH_PATTERNS:
            match = pattern.search(text)
            if match:
                target = match.group(1).lower()
                if target == "parrot":
                    target = "pirate"
                if target in self.personalities and target != self.current:
                    self.current = target
                    return self.personalities[target]["announce"]
        return None

    def list_modes(self):
        """Return a speakable list of available modes."""
        names = [p["name"] for p in self.personalities.values()]
        return "Available modes are: " + ", ".join(names) + "."
