"""
plugins/builtin/code_runner.py — Sandboxed Python execution.

Uses RestrictedPython to prevent access to OS, filesystem, network,
and other dangerous modules. Only pure computation is allowed.

Security model:
  - Whitelist-only builtins (no __import__, open, exec, eval)
  - No access to os, sys, subprocess, socket, etc.
  - 5-second execution timeout (via asyncio.wait_for)
  - stdout captured, not written to real stdout
  - Maximum output length enforced
"""

from __future__ import annotations

import asyncio
import io
import sys
from contextlib import redirect_stdout
from typing import Any

from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import safe_builtins, guarded_iter_unpack_sequence

from tgai_agent.plugins.base_plugin import BasePlugin, PluginError
from tgai_agent.plugins.registry import PluginRegistry
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

TIMEOUT_SECONDS = 5
MAX_OUTPUT_CHARS = 2000

# Allowed safe builtins (explicit whitelist)
_ALLOWED_BUILTINS: dict = {
    k: safe_builtins[k]
    for k in (
        "abs", "all", "any", "bin", "bool", "chr", "dict", "divmod",
        "enumerate", "filter", "float", "format", "frozenset", "getattr",
        "hasattr", "hash", "hex", "int", "isinstance", "issubclass",
        "iter", "len", "list", "map", "max", "min", "next", "oct",
        "ord", "pow", "print", "range", "repr", "reversed", "round",
        "set", "setattr", "slice", "sorted", "str", "sum", "tuple",
        "type", "zip",
    )
    if k in safe_builtins
}
_ALLOWED_BUILTINS["_getiter_"] = iter
_ALLOWED_BUILTINS["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence


def _run_code_sync(code: str) -> str:
    """Run sandboxed code synchronously; return captured stdout."""
    try:
        byte_code = compile_restricted(code, "<sandbox>", "exec")
    except SyntaxError as exc:
        raise PluginError(f"Syntax error: {exc}") from exc

    globs: dict[str, Any] = {
        **safe_globals,
        "__builtins__": _ALLOWED_BUILTINS,
        "__name__": "__sandbox__",
    }

    output_buffer = io.StringIO()
    try:
        with redirect_stdout(output_buffer):
            exec(byte_code, globs)  # noqa: S102 — intentional restricted exec
    except Exception as exc:
        raise PluginError(f"Runtime error: {exc}") from exc

    output = output_buffer.getvalue()
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n... [output truncated]"
    return output or "(no output)"


class CodeRunnerPlugin(BasePlugin):
    name = "run_python"
    description = (
        "Execute a small Python snippet in a secure sandbox. "
        "Only pure computation allowed — no file I/O, network, or OS access."
    )
    requires_confirmation = True
    is_safe = False
    parameter_schema = {
        "type": "object",
        "required": ["code"],
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
        },
    }

    async def execute(self, params: dict, context: dict) -> str:
        code = params.get("code", "").strip()
        if not code:
            raise PluginError("No code provided.")

        log.info(
            "code_runner.execute",
            user_id=context.get("user_id"),
            code_preview=code[:80],
        )

        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, _run_code_sync, code),
                timeout=TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise PluginError(f"Code execution timed out after {TIMEOUT_SECONDS}s.")

        return f"```\n{result}\n```"


# Self-register
PluginRegistry.register(CodeRunnerPlugin())
