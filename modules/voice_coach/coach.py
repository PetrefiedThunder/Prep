import logging
from typing import Optional


class VoiceCoach:
    def __init__(self, tone: str = "neutral", logger: Optional[logging.Logger] = None):
        self.tone = tone
        self.logger = logger or logging.getLogger(__name__)

    def coach(self, message: str) -> str:
        if self.tone == "gentle":
            prefix = "Just a tip: "
        elif self.tone == "direct":
            prefix = "Heads up: "
        else:
            prefix = ""
        output = prefix + message
        self.logger.info(output)
        return output
