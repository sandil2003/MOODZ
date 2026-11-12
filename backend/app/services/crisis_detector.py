"""Deterministic crisis and self-harm detection service.

Executes zero-latency regex evaluation to immediately catch emergency signals
before conversational LLMs are invoked.
"""

import re
from typing import Dict, Any, Optional, List, Pattern


class CrisisDetector:
    """Detects immediate self-harm or suicide risk in user messages with zero token overhead."""

    # Pre-compiled regular expression patterns for <10ms evaluation
    _COMPILED_PATTERNS: List[Pattern] = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"\bsuicid(e|al|es)?\b",
            r"\bself[- ]harm\w*\b",
            r"\bharm(ing)? myself\b",
            r"\bhurt(ing)? myself\b",
            r"\bkill(ing)? myself\b",
            r"\bend(ing)? my life\b",
            r"\bend(ing)? it all\b"
        ]
    ]

    def __init__(self):
        self.red_flag_patterns = self._COMPILED_PATTERNS

    async def check_crisis(self, text: Optional[str]) -> Dict[str, Any]:
        """Scan input text against crisis patterns.

        Returns:
            Dict containing 'type' ('immediate_risk' or 'none') and 'score' (1.0 or 0.0).
        """
        if not text or not isinstance(text, str):
            return {"type": "none", "score": 0.0}

        for compiled_pattern in self._COMPILED_PATTERNS:
            if compiled_pattern.search(text):
                return {"type": "immediate_risk", "score": 1.0}

        return {"type": "none", "score": 0.0}
