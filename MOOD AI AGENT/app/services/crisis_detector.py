import re
from typing import Dict, Any, Optional

class CrisisDetector:
    """
    Service to detect potential mental health crises or immediate self-harm risk in user input.
    """
    def __init__(self):
        self.red_flag_patterns = [
            r"\bsuicid(e|al)\b",
            r"\bself[- ]harm\b",
            r"\bharm\b(?!-)",
            r"\bhurt(ing)? myself\b",
            r"\bkill(ing)? myself\b",
            r"\bend(ing)? my life\b",
            r"\bend(ing)? it all\b"
        ]
        
    async def check_crisis(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return {"type": "none", "score": 0.0}
        for pattern in self.red_flag_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {"type": "immediate_risk", "score": 1.0}
        return {"type": "none", "score": 0.0}
