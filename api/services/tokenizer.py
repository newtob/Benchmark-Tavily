"""Shared token-estimation for every benchmark cell (both tables, all four
columns) — see specs/tavily-benchmark-app.md §6.

This is an APPROXIMATION, not exact Claude tokenization: `tiktoken` ships
OpenAI's tokenizers, not Anthropic's (which isn't published as an offline
library). `o200k_base` (GPT-4o/o-series/GPT-5 family's encoding) is used as
the closest readily-available stand-in for a modern large-vocabulary
tokenizer. Treat every `tokens` figure in this app as directionally useful
for *comparing* methods against each other, not as an exact Claude token
count.
"""

from __future__ import annotations

import tiktoken

ENCODING_NAME = "o200k_base"

_encoding = tiktoken.get_encoding(ENCODING_NAME)


def count_tokens(text: str) -> int:
    """Estimate the number of LLM tokens `text` would consume."""
    return len(_encoding.encode(text, disallowed_special=()))
