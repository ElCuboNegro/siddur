# ADR: 0061 — cache token pricing
"""
Token cost rate table for LLM models.

Rates in USD per 1,000,000 tokens (input / output).
Update this table as provider pricing changes.

Rate resolution order (see _resolve_rates):
  1. Exact model ID match in COST_RATES.
  2. Longest-prefix match in COST_RATES (covers dated variants such as
     "claude-haiku-4-5-20251001" → "claude-haiku-4-5").
  3. Longest-prefix match in FAMILY_RATES (covers models released after
     this table was last updated).

Incident 2026-06-10: claude-fable-5 / claude-opus-4-8 / claude-opus-4-7 /
claude-haiku-4-5-20251001 were missing from COST_RATES, estimate_cost()
returned None, and the Stop hook silently reported every session to Lodge
with estimated_cost_usd = 0. The family fallback exists so a model missing
from this table degrades to an approximate cost instead of a silent $0.
"""

from __future__ import annotations

from typing import Optional

# ADR-0061: prompt-cache token rates. Anthropic prices cache reads at 0.1x the
# input rate and cache writes (5-min TTL) at 1.25x. When a model entry lacks
# explicit cache rates, estimate_cost() derives them from the input rate with
# these multipliers — an approximation is strictly better than the $0 that
# cache tokens (90-97% of Claude Code session volume) were valued at before.
CACHE_READ_MULTIPLIER = 0.1
CACHE_WRITE_MULTIPLIER = 1.25

# { model_id: {"input": $/M tokens, "output": $/M tokens} }
COST_RATES: dict[str, dict[str, float]] = {
    # --- Anthropic Claude ---
    "claude-fable-5": {"input": 10.00, "output": 50.00},
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
    "claude-opus-4-7": {"input": 5.00, "output": 25.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-opus-4-5": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    # --- Google Gemini (Vertex AI) ---
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30},
    "gemini-2.0-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash-8b": {"input": 0.0375, "output": 0.15},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    # --- OpenAI (for teams using GPT via openai SDK) ---
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}

# Fallback rates by model family, used when a model is not in COST_RATES.
# Longest matching prefix wins. Keep family rates aligned with the latest
# known generation of each family — an approximate cost is strictly better
# than the silent $0 that caused the 2026-06-10 reporting outage.
FAMILY_RATES: dict[str, dict[str, float]] = {
    "claude-fable": {"input": 10.00, "output": 50.00},
    "claude-opus": {"input": 5.00, "output": 25.00},
    "claude-sonnet": {"input": 3.00, "output": 15.00},
    "claude-haiku": {"input": 0.80, "output": 4.00},
    # Unknown Claude family: assume frontier-tier so the spend is visible.
    "claude": {"input": 10.00, "output": 50.00},
    "gemini": {"input": 1.25, "output": 5.00},
    "gpt": {"input": 2.50, "output": 10.00},
    "o1": {"input": 15.00, "output": 60.00},
    "o3": {"input": 10.00, "output": 40.00},
}


def _longest_prefix(
    model: str, table: dict[str, dict[str, float]]
) -> Optional[dict[str, float]]:
    best_key = ""
    for key in table:
        if model.startswith(key) and len(key) > len(best_key):
            best_key = key
    return table.get(best_key) if best_key else None


def _resolve_rates(model: str) -> Optional[dict[str, float]]:
    """Resolve rates: exact match, then table prefix, then family fallback."""
    exact = COST_RATES.get(model)
    if exact is not None:
        return exact
    return _longest_prefix(model, COST_RATES) or _longest_prefix(model, FAMILY_RATES)


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> Optional[float]:
    """
    Return estimated cost in USD, or None if no rate (exact, prefix, or
    family fallback) is known for the model.

    Cache tokens (ADR-0061) are priced with the model's explicit
    "cache_read"/"cache_write" rates when present, otherwise derived from the
    input rate (0.1x read / 1.25x write, Anthropic's published multipliers).
    """
    rates = _resolve_rates(model)
    if rates is None:
        return None
    cache_read_rate = rates.get("cache_read", rates["input"] * CACHE_READ_MULTIPLIER)
    cache_write_rate = rates.get("cache_write", rates["input"] * CACHE_WRITE_MULTIPLIER)
    cost = (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + cache_read_tokens * cache_read_rate
        + cache_write_tokens * cache_write_rate
    ) / 1_000_000
    return round(cost, 8)


def get_provider(model: str) -> str:
    """Infer the provider name from the model ID."""
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gemini"):
        return "google"
    if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
        return "openai"
    return "unknown"
