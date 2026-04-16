"""
Shared text helpers with no intra-package imports (safe to import from anywhere).
"""
import re


def _strip_think(text: str) -> str:
    """Remove Sarvam reasoning model's <think>...</think> block.
    Strategy: if </think> exists, take everything after it.
    If only <think> with no closing tag, strip from <think> onward.
    This handles cases where the model wraps JSON inside <think>.
    """
    if not text:
        return ''
    # Case 1: properly closed — take content after </think>
    if '</think>' in text:
        after = text.split('</think>', 1)[1].strip()
        if after:
            return after
        # nothing after </think> — extract what was inside
        inner = re.search(r'<think>(.*?)</think>', text, re.DOTALL)
        return inner.group(1).strip() if inner else text.strip()
    # Case 2: unclosed <think> tag — strip it and everything before first {
    if '<think>' in text:
        text = text.split('<think>', 1)[1]
        # find first JSON-like start
        brace = text.find('{')
        return text[brace:].strip() if brace != -1 else text.strip()
    return text.strip()
