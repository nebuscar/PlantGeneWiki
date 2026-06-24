"""
Orchestrator: Claude tool_use loop with sliding-window session memory.

Supports two API modes:
  - anthropic: official Anthropic SDK (default), supports custom base_url
  - openai:    OpenAI-compatible SDK (OpenRouter, local models, proxies)

Responsibilities:
  - Maintain a sliding message window (SESSION_WINDOW messages)
  - Register base tools + auto-discovered Skills as LLM tools
  - Drive the tool_use loop until end_turn
  - Truncate tool results to avoid context overflow
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import AsyncGenerator

import anthropic
import openai

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SESSION_WINDOW, get_system_prompt
from tools import (
    get_gene_info, query_homolog, search_by_annotation, compare_protein_props,
    expression_query, go_kegg_enrichment, search_literature, get_lit_summary,
)
import skills as _skills_registry

MAX_TOOL_RESULT_CHARS = 8000


# ── API 配置 ─────────────────────────────────────────────────────────────────

@dataclass
class APIConfig:
    api_key:  str
    model:    str
    base_url: str | None = None
    mode:     str = "anthropic"   # "anthropic" | "openai"

    @classmethod
    def default(cls) -> "APIConfig":
        return cls(
            api_key  = ANTHROPIC_API_KEY or "placeholder",
            model    = CLAUDE_MODEL,
            base_url = None,
            mode     = "anthropic",
        )

    @classmethod
    def from_session(
        cls,
        api_key:  str | None,
        model:    str | None,
        base_url: str | None,
        mode:     str | None,
    ) -> "APIConfig":
        default = cls.default()
        return cls(
            api_key  = api_key  or default.api_key,
            model    = model    or default.model,
            base_url = base_url or default.base_url,
            mode     = mode     or default.mode,
        )


# ── 工具路由 ─────────────────────────────────────────────────────────────────

def _dispatch(tool_name: str, tool_input: dict) -> str:
    try:
        match tool_name:
            case "get_gene_info":         result = get_gene_info(**tool_input)
            case "query_homolog":         result = query_homolog(**tool_input)
            case "search_by_annotation":  result = search_by_annotation(**tool_input)
            case "compare_protein_props": result = compare_protein_props(**tool_input)
            case "expression_query":      result = expression_query(**tool_input)
            case "go_kegg_enrichment":    result = go_kegg_enrichment(**tool_input)
            case "search_literature":     result = search_literature(**tool_input)
            case "get_lit_summary":       result = get_lit_summary(**tool_input)
            case _ if tool_name in _skills_registry.SKILLS:
                result = _skills_registry.dispatch(tool_name, tool_input)
            case _:
                result = {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        result = {"error": f"工具执行失败：{e}"}

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if len(text) > MAX_TOOL_RESULT_CHARS:
        text = text[:MAX_TOOL_RESULT_CHARS] + f"\n...[已截断，原长 {len(text)} 字符]"
    return text


# ── Anthropic 格式工具定义 ────────────────────────────────────────────────────

TOOLS_ANTHROPIC: list[dict] = [
    {
        "name": "get_gene_info",
        "description": (
            "查询单个基因的详细信息：基因结构（染色体坐标、长度、链方向）、"
            "蛋白理化性质（pI、分子量、氨基酸长度）、功能注释（GO、KEGG、Pfam）。"
            "适用于：了解某基因全貌、查坐标、查功能。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "species": {"type": "string", "description": "物种名，如 Arabidopsis_thaliana"},
                "gene_id": {"type": "string", "description": "基因 ID，如 AT1G01010"},
                "fields":  {"type": "array", "items": {"type": "string",
                            "enum": ["structure", "properties", "annotation"]}},
            },
            "required": ["species", "gene_id"],
        },
    },
    {
        "name": "query_homolog",
        "description": (
            "查询属内物种间一对一直系同源基因（GeneTribe BSR/RBH）。"
            "适用于：找同源基因、了解基因属内保守性、为跨物种比较准备 ID 列表。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "genus":       {"type": "string", "description": "属名，如 Arabidopsis"},
                "gene_id":     {"type": "string", "description": "参考基因 ID（可选）"},
                "ref_species": {"type": "string", "description": "指定参考物种（可选）"},
                "min_bsr":     {"type": "number", "description": "BSR 阈值，默认 0.3"},
            },
            "required": ["genus"],
        },
    },
    {
        "name": "search_by_annotation",
        "description": (
            "按功能注释检索物种内的基因。调用前请将用户自然语言转为具体 term。"
            "适用于：找含某结构域基因、找参与某通路基因、按功能关键词找基因。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "species":    {"type": "string"},
                "pfam_ids":   {"type": "array", "items": {"type": "string"}},
                "go_terms":   {"type": "array", "items": {"type": "string"}},
                "kegg_kos":   {"type": "array", "items": {"type": "string"}},
                "keywords":   {"type": "array", "items": {"type": "string"}},
                "match_mode": {"type": "string", "enum": ["any", "all"]},
                "limit":      {"type": "integer"},
            },
            "required": ["species"],
        },
    },
    {
        "name": "compare_protein_props",
        "description": "对比多个基因蛋白理化性质（pI、分子量、长度）。通常先用 query_homolog 获取基因列表。",
        "input_schema": {
            "type": "object",
            "properties": {
                "targets": {
                    "type": "array",
                    "items": {"type": "object",
                              "properties": {"species": {"type": "string"}, "gene_id": {"type": "string"}},
                              "required": ["species", "gene_id"]},
                },
                "sort_by": {"type": "string", "enum": ["pi", "mol_weight", "prot_length"]},
            },
            "required": ["targets"],
        },
    },
    {
        "name": "expression_query",
        "description": (
            "查询基因 RNA-seq 表达量（TPM）。\n"
            "mode='tissue'：按组织聚合 → 适合「哪个组织表达最高」。\n"
            "mode='condition'：保留处理条件 → 适合「胁迫下的变化」。\n"
            "include_treatment=False（默认）：仅对照组。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "species":           {"type": "string"},
                "gene_ids":          {"type": "array", "items": {"type": "string"}},
                "mode":              {"type": "string", "enum": ["tissue", "condition"]},
                "tissues":           {"type": "array", "items": {"type": "string"}},
                "include_treatment": {"type": "boolean"},
            },
            "required": ["species", "gene_ids"],
        },
    },
    {
        "name": "search_literature",
        "description": "在已上传文献中语义检索，返回相关段落和来源。仅覆盖管理员上传的文献。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":   {"type": "string"},
                "filters": {"type": "object",
                            "properties": {"gene": {"type": "string"}, "species": {"type": "string"},
                                           "year_from": {"type": "integer"}, "year_to": {"type": "integer"}}},
                "top_k":   {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_lit_summary",
        "description": "获取某基因/主题的文献综述摘要（预生成缓存，毫秒级）。给宏观综述，search_literature 给具体证据。",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic":   {"type": "string"},
                "filters": {"type": "object"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "go_kegg_enrichment",
        "description": "对基因列表做 GO/KEGG 富集分析（Fisher 检验 + BH FDR 校正）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "species":     {"type": "string"},
                "gene_ids":    {"type": "array", "items": {"type": "string"}},
                "types":       {"type": "array", "items": {"type": "string",
                                "enum": ["go_bp", "go_mf", "go_cc", "kegg"]}},
                "p_threshold": {"type": "number"},
            },
            "required": ["species", "gene_ids"],
        },
    },

]

# Append skill tool definitions loaded from skills/*/SKILL.md
TOOLS_ANTHROPIC = TOOLS_ANTHROPIC + _skills_registry.get_skill_tools()


def _to_openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name":        t["name"],
                "description": t["description"],
                "parameters":  t["input_schema"],
            },
        }
        for t in tools
    ]


# blast_search / sequence_fetch 仅登录用户可用（设计文档 1.1 节）
_GUEST_RESTRICTED_SKILLS = {"blast_search", "sequence_fetch"}

_GUEST_TOOLS = {
    "get_gene_info", "query_homolog", "search_by_annotation", "compare_protein_props",
    "expression_query", "go_kegg_enrichment", "search_literature", "get_lit_summary",
} | (set(_skills_registry.SKILLS.keys()) - _GUEST_RESTRICTED_SKILLS)

ROLE_TOOLS: dict[str, set[str]] = {
    "guest": _GUEST_TOOLS,
    "user":  {t["name"] for t in TOOLS_ANTHROPIC},
    "admin": {t["name"] for t in TOOLS_ANTHROPIC},
}


# ── Anthropic 模式 ────────────────────────────────────────────────────────────

async def _run_anthropic(
    messages: list[dict],
    active_tools: list[dict],
    cfg: APIConfig,
    system_prompt: str,
) -> AsyncGenerator[str, None]:
    kwargs = {"api_key": cfg.api_key}
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url

    client = anthropic.Anthropic(**kwargs)

    for _turn in range(5):
        response = client.messages.create(
            model      = cfg.model,
            max_tokens = 4096,
            system     = system_prompt,
            tools      = active_tools,
            messages   = messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    yield block.text
            return

        if response.stop_reason != "tool_use":
            for block in response.content:
                if hasattr(block, "text"):
                    yield block.text
            return

        # 执行工具
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result_text = _dispatch(block.name, block.input)
            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": block.id,
                "content":     result_text,
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user",      "content": tool_results})

    yield "（工具调用超出最大轮次，请简化问题后重试）"


# ── OpenAI 兼容模式 ───────────────────────────────────────────────────────────

async def _run_openai(
    messages: list[dict],
    active_tools: list[dict],
    cfg: APIConfig,
    system_prompt: str,
) -> AsyncGenerator[str, None]:
    kwargs: dict = {"api_key": cfg.api_key}
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url

    client   = openai.OpenAI(**kwargs)
    oa_tools = _to_openai_tools(active_tools)

    # OpenAI 消息格式：system 在 messages 列表里
    oa_messages = [{"role": "system", "content": system_prompt}] + messages

    for _turn in range(5):
        response = client.chat.completions.create(
            model    = cfg.model,
            messages = oa_messages,
            tools    = oa_tools if oa_tools else openai.NOT_GIVEN,
        )

        choice = response.choices[0]

        if choice.finish_reason != "tool_calls":
            yield choice.message.content or ""
            return

        # 执行工具
        oa_messages.append(choice.message)   # assistant message with tool_calls

        for tc in (choice.message.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            result_text = _dispatch(tc.function.name, args)
            oa_messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      result_text,
            })

    yield "（工具调用超出最大轮次，请简化问题后重试）"


# ── 统一入口 ──────────────────────────────────────────────────────────────────

async def run(
    user_message: str,
    history: list[dict],
    role: str = "user",
    api_key:  str | None = None,
    model:    str | None = None,
    base_url: str | None = None,
    mode:     str | None = None,
) -> AsyncGenerator[str, None]:
    """
    执行一次完整推理（含 tool_use 循环），流式 yield 最终回复文本。

    参数优先级：调用方传入 > 环境变量默认值
    """
    cfg = APIConfig.from_session(api_key, model, base_url, mode)

    available_tool_names = ROLE_TOOLS.get(role, ROLE_TOOLS["guest"])
    active_tools = [t for t in TOOLS_ANTHROPIC if t["name"] in available_tool_names]

    messages      = history[-SESSION_WINDOW:] + [{"role": "user", "content": user_message}]
    system_prompt = get_system_prompt(role)

    if cfg.mode == "openai":
        async for chunk in _run_openai(messages, active_tools, cfg, system_prompt):
            yield chunk
    else:
        async for chunk in _run_anthropic(messages, active_tools, cfg, system_prompt):
            yield chunk
