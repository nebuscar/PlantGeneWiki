from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class SkillDef:
    name:            str
    label:           str
    description:     str
    icon:            str
    triggers:        list[str]
    input_schema:    dict
    starter_label:   str
    starter_message: str
    run:             Callable

    def to_anthropic_tool(self) -> dict:
        trigger_hint = "  ".join(f'"{t}"' for t in self.triggers[:3])
        return {
            "name": self.name,
            "description": (
                f"[SKILL] {self.description.strip()}\n"
                f"Trigger when user says: {trigger_hint}"
            ),
            "input_schema": self.input_schema,
        }
