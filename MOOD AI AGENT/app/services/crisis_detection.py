import re
from typing import Optional, Dict

class CrisisDetector:
    def __init__(self):
        self.red_flag_keywords = [
            r"suicide",
            r"harm",
            r"hurt myself",
            r"end it all",
            r"keyboard is bad"
        ]
    async def check_crisis(self, text: str) -> Optional[Dict]:
        print(f"🔍 Checking crisis for text: '{text}'")
        for pattern in self.red_flag_keywords:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    "type": "immediate_risk",
                    "score": 1.0
                }

        return {
            "type": "none",
            "score": 0.0
        }

    