# hooks.py

import asyncio
import sys
from dataclasses import dataclass
from typing import Callable, Awaitable, List

@dataclass
class HookHandler:
    threshold: int
    func: Callable[[dict], Awaitable[None]]


async def _run_hook(hook: HookHandler, log_dict: dict, timeout: float = 5.0):
    try:
        return await asyncio.wait_for(hook.func(log_dict), timeout)
    except Exception as e:
        return e


async def dispatch_hooks(log_dict: dict, level_value: int, handlers: List[HookHandler]):
    """Run all hooks for the given log level. Fail-safe. Never throws."""
    hook_tasks = [
        _run_hook(hook, log_dict)
        for hook in handlers
        if level_value >= hook.threshold
    ]

    if not hook_tasks:
        return

    results = await asyncio.gather(*hook_tasks, return_exceptions=True)

    for hook, result in zip(handlers, results):
        if isinstance(result, Exception):
            hook_name = getattr(hook.func, "__name__", repr(hook.func))
            print(f"[Chronologix] Hook '{hook_name}' failed: {result}", file=sys.stderr)
