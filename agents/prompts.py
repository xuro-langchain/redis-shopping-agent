"""
Prompt management module.

Prompts are stored in Redis under keys `prompts:<name>`. On import, this module
seeds Redis from prompts.json (for any missing keys) and then loads all prompts
from Redis.

Redis is the runtime source of truth - prompts can be edited there without
redeploying. Use `seed_prompts(force=True)` to reset to defaults from JSON.
"""

import json
from pathlib import Path
from typing import Dict

from agents.utils import get_redis_client


# Redis key prefix for prompts
PROMPT_PREFIX = "prompts"

# Path to the JSON file containing default prompts
PROMPTS_JSON_PATH = Path(__file__).parent / "seed" / "prompts.json"


def _load_defaults_from_json() -> Dict[str, str]:
    """Load default prompts from the JSON file."""
    with open(PROMPTS_JSON_PATH, "r") as f:
        return json.load(f)


def seed_prompts(force: bool = False) -> None:
    """
    Seed Redis with prompts from prompts.json.

    Args:
        force: If True, overwrite all existing prompts. If False, only set
               prompts that don't already exist in Redis.
    """
    client = get_redis_client()
    defaults = _load_defaults_from_json()

    for name, content in defaults.items():
        key = f"{PROMPT_PREFIX}:{name}"
        if force or not client.exists(key):
            client.set(key, content)


def get_prompt(name: str) -> str:
    """
    Get a prompt from Redis by name.

    Args:
        name: The prompt name (without the 'prompts:' prefix)

    Returns:
        The prompt content as a string

    Raises:
        KeyError: If the prompt doesn't exist in Redis
    """
    client = get_redis_client()
    key = f"{PROMPT_PREFIX}:{name}"
    value = client.get(key)
    if value is None:
        raise KeyError(f"Prompt '{name}' not found in Redis. Run seed_prompts() first.")
    return value.decode("utf-8")


def _initialize_prompts() -> None:
    """Seed prompts on module import (only sets missing keys)."""
    seed_prompts(force=False)


# ------------------------------------------------------------
# Module Initialization
# ------------------------------------------------------------
# Seed Redis with any missing prompts from JSON
_initialize_prompts()

# Load all prompts from Redis and expose as module-level variables
supervisor_system_prompt: str = get_prompt("supervisor_system_prompt")
invoice_subagent_prompt: str = get_prompt("invoice_subagent_prompt")
music_subagent_prompt: str = get_prompt("music_subagent_prompt")
concert_subagent_prompt: str = get_prompt("concert_subagent_prompt")
extract_customer_info_prompt: str = get_prompt("extract_customer_info_prompt")
verify_customer_info_prompt: str = get_prompt("verify_customer_info_prompt")
create_memory_prompt: str = get_prompt("create_memory_prompt")
