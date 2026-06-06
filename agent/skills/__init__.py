"""
Skills auto-loader.

Discovers every subdirectory under skills/ that contains SKILL.md + handler.py,
parses the YAML frontmatter from SKILL.md, and registers a SkillDef entry.
"""
from __future__ import annotations

import importlib
import re
from pathlib import Path

import yaml

from skills.base import SkillDef

_SKILLS_DIR = Path(__file__).parent

SKILLS: dict[str, SkillDef] = {}


def _parse_frontmatter(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        raise ValueError(f"No YAML frontmatter found in {md_path}")
    return yaml.safe_load(m.group(1))


def _load():
    for skill_dir in sorted(_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        skill_md    = skill_dir / "SKILL.md"
        handler_py  = skill_dir / "handler.py"
        if not skill_md.exists() or not handler_py.exists():
            continue
        try:
            meta   = _parse_frontmatter(skill_md)
            module = importlib.import_module(f"skills.{skill_dir.name}.handler")
            SKILLS[meta["name"]] = SkillDef(
                name            = meta["name"],
                label           = meta["label"],
                description     = meta["description"],
                icon            = meta.get("icon", ""),
                triggers        = meta.get("triggers", []),
                input_schema    = meta["input_schema"],
                starter_label   = meta["starter"]["label"],
                starter_message = meta["starter"]["message"],
                run             = module.run,
            )
        except Exception as e:
            print(f"[skills] Failed to load {skill_dir.name}: {e}")


_load()


def get_skill_tools() -> list[dict]:
    return [s.to_anthropic_tool() for s in SKILLS.values()]


def dispatch(skill_name: str, tool_input: dict):
    skill = SKILLS.get(skill_name)
    if skill is None:
        return {"error": f"Unknown skill: {skill_name}"}
    return skill.run(**tool_input)


def get_starters():
    import chainlit as cl
    return [
        cl.Starter(
            label   = s.starter_label,
            message = s.starter_message,
        )
        for s in SKILLS.values()
    ]
